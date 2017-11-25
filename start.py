import web
import psycopg2
from geojson import Feature, Point, FeatureCollection
import json

urls = (
    '/', 'Index',
    '/api/update', 'ApiUpdate',
    '/api/find_closest', 'ApiFindClosest',
    '/api/country_stats', 'ApiCountryStats'
)

render = web.template.render('templates/')
conn_string = "host='localhost' dbname='ter' user='postgres' password='password'"
# print the connection string we will use to connect
print "Connecting to database\n ->%s" % (conn_string)
# get a connection, if a connect cannot be made an exception will be raised here
conn = psycopg2.connect(conn_string)
# conn.cursor will return a cursor object, you can use this cursor to perform queries
cursor = conn.cursor()
print "Connected to DB!\n"



def load_incidents(year_min = None, year_max = None, att_types = None):
    print type(att_types)
    cursor.execute("SELECT jsonb_build_object( \
                                        'type', 'FeatureCollection', \
                                        'features', jsonb_agg(feature) \
                                        ) \
                    FROM ( \
                        SELECT jsonb_build_object( \
                                                    'type',       'Feature', \
                                                    'id',         objectid, \
                                                    'geometry',   ST_AsGeoJSON(shape)::jsonb, \
                                                    'properties', to_jsonb(row) - 'objectid' - 'shape' \
                                                ) AS feature \
                        FROM (SELECT objectid,shape,iyear,imonth,iday,country_txt,alternative_txt, \
                        weaptype1_txt,nkill,nwound,attacktype1_txt,city FROM public.globalterrorismdb_0617dist \
                              WHERE iyear BETWEEN %s AND %s AND\
                              attacktype1_txt IN %s LIMIT 200000) row) features;", (year_min, year_max, tuple(att_types)))
    # retrieve the records from the database1
    records = cursor.fetchone()
    return json.dumps(records[0])

def find_closest_attack(year_min = None , year_max = None, att_types = None,
                        lat = None, lng = None):
    # a = cursor.mogrify("SELECT jsonb_build_object( \
    #                                     'type', 'FeatureCollection', \
    #                                     'features', jsonb_agg(feature) \
    #                                     ) \
    #                 FROM ( \
    #                     SELECT jsonb_build_object( \
    #                                                 'type',       'Feature', \
    #                                                 'geometry',   ST_AsGeoJSON(line)::jsonb, \
    #                                                 'properties', to_jsonb(row) - 'line' \
    #                                             ) AS feature \
    #                     FROM (WITH point_table AS (SELECT ST_SetSRID(ST_MakePoint(%s, %s), 4326) AS point),\
    #                                att_table AS (SELECT shape \
    #                                              FROM public.globalterrorismdb_0617dist \
    #                                              WHERE iyear BETWEEN %s AND %s AND attacktype1_txt IN %s LIMIT 200000) \
    #                                              SELECT ST_Distance(point::geography,shape::geography) AS dist, \
    #                                                     ST_MakeLine(point,shape) AS linee FROM point_table \
    #                                              CROSS JOIN att_table \
    #                                              ORDER BY dist ASC \
    #                                              LIMIT 1) row) features;", (lng,lat,year_min, year_max, tuple(att_types)))

    # print a
    cursor.execute("SELECT jsonb_build_object( \
                                        'type', 'FeatureCollection', \
                                        'features', jsonb_agg(feature) \
                                        ) \
                    FROM ( \
                        SELECT jsonb_build_object( \
                                                    'type',       'Feature', \
                                                    'geometry',   ST_AsGeoJSON(line)::jsonb, \
                                                    'properties', to_jsonb(row) - 'line' \
                                                ) AS feature \
                        FROM (WITH point_table AS (SELECT ST_SetSRID(ST_MakePoint(%s, %s), 4326) AS point), \
                                   att_table AS (SELECT shape \
                                                 FROM public.globalterrorismdb_0617dist \
                                                 WHERE iyear BETWEEN %s AND %s AND attacktype1_txt IN %s LIMIT 200000) \
                              SELECT ST_Distance(point::geography, shape::geography) AS dist, \
                              ST_MakeLine(point,shape) AS line FROM point_table \
                              CROSS JOIN att_table \
                              ORDER BY dist ASC \
                              LIMIT 1) row) features;", (lng,lat,year_min, year_max, tuple(att_types)))
    # retrieve the records from the database1
    records = cursor.fetchone()
    print records
    return json.dumps(records[0])


def find_country_stats(year_min = None, year_max = None, att_types = None):
    cursor.execute("SELECT jsonb_build_object( \
                                        'type', 'FeatureCollection', \
                                        'features', jsonb_agg(feature) \
                                        ) \
                    FROM ( \
                        SELECT jsonb_build_object( \
                                                    'type',       'Feature', \
                                                    'geometry',   ST_AsGeoJSON(geom)::jsonb, \
                                                    'properties', to_jsonb(row) - 'geom' \
                                                ) AS feature \
                        FROM (WITH bord AS (SELECT COUNT(borders.name) AS cnt, borders.name FROM public.globalterrorismdb_0617dist AS ter \
                                            CROSS JOIN public.tm_world_borders AS borders \
                                            WHERE iyear BETWEEN %s AND %s AND attacktype1_txt IN %s \
                                            AND ST_Contains(borders.geom,ter.shape) \
                                            GROUP BY borders.name) \
                            SELECT bord.cnt,bord.name,borders.geom FROM bord \
                            JOIN public.tm_world_borders AS borders ON bord.name = borders.name) row) features;", (year_min, year_max, tuple(att_types)))
    # retrieve the records from the database1
    records = cursor.fetchone()
    #print records
    max_cnt = 0

    for x in records[0]['features']:
        if max_cnt < x['properties']['cnt']:
            max_cnt = x['properties']['cnt']

    for x in records[0]['features']:
        x['properties']['color'] = rgb_to_hex(rgb(x['properties']['cnt'], maximum = max_cnt))

    return json.dumps(records[0])

def load_all_att_types():
    cursor.execute("SELECT DISTINCT attacktype1_txt FROM globalterrorismdb_0617dist;")
    # retrieve the records from the database
    records = cursor.fetchall()
    records_list = []
    for x in records:
        records_list.append(x[0])
    return records_list

def rgb(value, minimum = 0, maximum = 22000):
    minimum, maximum = float(minimum), float(maximum)
    ratio = (value-minimum) / (maximum - minimum)
    #b = int(max(0, 255*(1 - ratio)))
    b = int(max(0, 255*(ratio)))
    g = 0
    r = 0
    #g = 255 - b - r
    return r, g, b

def rgb_to_hex(colors):
    """Return color as #rrggbb for the given color values."""
    return '#%02x%02x%02x' % (colors[0], colors[1], colors[2])

def load_year_range():
    cursor.execute("SELECT MIN(iyear),MAX(iyear) FROM globalterrorismdb_0617dist")
    # retrieve the records from the database
    records = cursor.fetchone()
    return {"min":records[0],"max":records[1]}


def update_map(min_year = None , max_year = None, incident_types = None):
    data = {}
    data['year_range'] = {}
    if min_year == None or max_year == None:
        data['year_range'] = load_year_range()
    else:
        data['year_range']['min'] = min_year
        data['year_range']['max'] = max_year

    if incident_types == None:
        data['att_types'] = load_all_att_types()
        data['geojson'] = load_incidents(data['year_range']['min'], data['year_range']['max'], [data['att_types'][0]])
    else:
        data['att_types'] = incident_types
        data['geojson'] = load_incidents(data['year_range']['min'], data['year_range']['max'], data['att_types'])

    return data


class Index:
    def GET(self):
        data = update_map()
        return render.index(data)

class ApiUpdate:
    def POST(self):
        user_data = json.loads(web.data())
        print user_data
        if not user_data['checked_checkboxes']:
            return None

        data = update_map(min_year = user_data['min'], max_year = user_data['max'], incident_types = user_data['checked_checkboxes'])
        return data['geojson']

class ApiFindClosest:
    def POST(self):
        user_data = json.loads(web.data())
        print user_data
        if not user_data['checked_checkboxes']:
            return None

        data = find_closest_attack(year_min = user_data['min'], year_max = user_data['max'], 
                                   att_types = user_data['checked_checkboxes'],
                                   lat = user_data['lat'], lng = user_data['lng'])
        return data

class ApiCountryStats:
    def POST(self):
        user_data = json.loads(web.data())
        print user_data
        if not user_data['checked_checkboxes']:
            return None

        data = find_country_stats(year_min = user_data['min'], year_max = user_data['max'], 
                                  att_types = user_data['checked_checkboxes'])
        return data
        

if __name__ == "__main__": 
    app = web.application(urls, globals())
    app.run()    