import sys
import web
import psycopg2
import geojson
import simplejson as json
import logging 

logging.basicConfig(format='%(asctime)s %(message)s', filename='/var/log/maproulette/maproulette.log',level=logging.DEBUG)

urls = (
    '/count/', 'getcount',
    '/store/(.*)/(-*\d+)', 'storeresult',
    '/get/', 'getcandidate'
)

sys.stdout = sys.stderr

app = web.application(urls, globals(), autoreload=False)
application = app.wsgifunc()

class getcandidate:        
    def GET(self):
        conn = psycopg2.connect("host=localhost dbname=osm user=osm password=osm")
        cur = conn.cursor()
        sql = """SELECT ST_AsGeoJSON(linestring), id  FROM 
                mr_ways_no_lanes_challenge 
                WHERE NOT done AND type = 'motorway' AND (current_timestamp - donetime) > '1 hour' 
                ORDER BY random LIMIT 1"""
        logging.debug(sql)
        cur.execute(sql)
        recs = cur.fetchall()
        (way,wayid) = recs[0]
#lock the way
        cur2 = conn.cursor()
        sql = cur2.mogrify("SELECT mr_upsert(%s::boolean,%s)", (0,wayid))
        logging.debug(sql)
        cur2.execute("SELECT mr_upsert(%s::boolean,%s)", (0,wayid))
        out = geojson.FeatureCollection([geojson.Feature(geometry=geojson.loads(way),properties={"id": wayid})])
        conn.commit();
        cur2.close()
        cur.close()
        return geojson.dumps(out)

class storeresult:        
    def PUT(self,osmid,done):
        conn = psycopg2.connect("host=localhost dbname=osm user=osm password=osm")
        cur = conn.cursor()
        if not osmid:
            return web.badrequest();
        try:
            cur.execute("SELECT mr_upsert(%s::boolean,%s)", (done,osmid))
            conn.commit()
        except Exception, e:
            print e
            return web.badrequest()
        finally:
            cur.close()
        return True

class getcount:
    """returns a list containing total count remaining, fixed in last hour, fixed in last day, seen in last hour, seen in last day"""
    def GET(self):
        result = []
        conn = psycopg2.connect("host=localhost dbname=osm user=osm password=osm")
        cur = conn.cursor()
        cur.execute("select count(1) from mr_ways_no_lanes_challenge where type = 'motorway' and not done;")
        result.append(cur.fetchone()[0])
        cur.execute("select count(1) FROM tnav_ways_no_lanes_mrstatus WHERE now() - donetime < interval '1 hour' and done")
        result.append(cur.fetchone()[0])
        cur.execute("select count(1) FROM tnav_ways_no_lanes_mrstatus WHERE now() - donetime < interval '1 day' and done")
        result.append(cur.fetchone()[0])
        cur.execute("select count(1) FROM tnav_ways_no_lanes_mrstatus WHERE now() - donetime < interval '1 hour'")
        result.append(cur.fetchone()[0])
        cur.execute("select count(1) FROM tnav_ways_no_lanes_mrstatus WHERE now() - donetime < interval '1 day'")
        result.append(cur.fetchone()[0])
        cur.close()
        return json.dumps(result)
        
if __name__ == "__main__":
    app.run()
