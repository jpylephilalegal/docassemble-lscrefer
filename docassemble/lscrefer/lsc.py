import requests
import copy
import json
import re
import sys
from six import text_type
from io import open
from docassemble.base.util import Organization, DADict, path_and_mimetype, DARedis, DAList, Address, objects_from_file
from math import sin, cos, sqrt, atan2, radians

__all__ = ['lsc_program_for', 'offices_for', 'cities_near', 'poverty_percentage']

base_url = "https://services3.arcgis.com/n7h3cEoHTyNCwjCf/ArcGIS/rest/services/BasicField_ServiceAreas2019/FeatureServer/0/query"
base_params = {'where': 'OBJECTID>=0', 'objectIds': '', 'time': '', 'geometryType': 'esriGeometryPoint', 'inSR': '{"wkid": 4326}', 'spatialRel': 'esriSpatialRelWithin', 'resultType': 'none', 'distance': '0.0', 'units': 'esriSRUnit_Meter', 'returnGeodetic': 'false', 'outFields': '*', 'returnGeometry': 'false', 'returnCentroid': 'false', 'multipatchOption': 'xyFootprint', 'maxAllowableOffset': '', 'geometryPrecision': '', 'outSR': '{"wkid": 4326}', 'datumTransformation': '', 'applyVCSProjection': 'false', 'returnIdsOnly': 'false', 'returnUniqueIdsOnly': 'false', 'returnCountOnly': 'false', 'returnExtentOnly': 'false', 'returnQueryGeometry': 'false', 'returnDistinctValues': 'false', 'orderByFields': '', 'groupByFieldsForStatistics': '', 'outStatistics': '', 'having': '', 'resultOffset': '', 'resultRecordCount': '', 'returnZ': 'false', 'returnM': 'false', 'returnExceededLimitFeatures': 'true', 'quantizationParameters': '', 'sqlFormat': 'none', 'f': 'pjson', 'token': ''}

office_base_url = "https://services3.arcgis.com/n7h3cEoHTyNCwjCf/ArcGIS/rest/services/LSC_offices_grantees_main_branch_(Public)/FeatureServer/0/query"
office_base_params = {'objectIds': '', 'time': '', 'geometry': '', 'geometryType': 'esriGeometryEnvelope', 'inSR': '', 'spatialRel': 'esriSpatialRelIntersects', 'resultType': 'none', 'distance': '0.0', 'units': 'esriSRUnit_Meter', 'returnGeodetic': 'false', 'outFields': '*', 'returnGeometry': 'false', 'multipatchOption': 'xyFootprint', 'maxAllowableOffset': '', 'geometryPrecision': '', 'outSR': '', 'datumTransformation': '', 'applyVCSProjection': 'false', 'returnIdsOnly': 'false', 'returnUniqueIdsOnly': 'false', 'returnCountOnly': 'false', 'returnExtentOnly': 'false', 'returnQueryGeometry': 'false', 'returnDistinctValues': 'false', 'orderByFields': '', 'groupByFieldsForStatistics': '', 'outStatistics': '', 'having': '', 'resultOffset': '', 'resultRecordCount': '', 'returnZ': 'false', 'returnM': 'false', 'returnExceededLimitFeatures': 'true', 'quantizationParameters': '', 'sqlFormat': 'none', 'f': 'pjson', 'token': ''}

lsc_programs = dict()
lsc_programs_by_rin = dict()
lsc_programs_by_serv_a = dict()

poverty = objects_from_file("docassemble.lscrefer:data/sources/poverty.yml")

def poverty_percentage(household_income, household_size, state):
    #sys.stderr.write("poverty_percentage start\n")
    try:
        household_size = int(household_size)
        assert household_size > 0
    except:
        raise Exception("poverty_percentage: invalid household size")
    if state == 'HI':
        index_num = 2
    elif state == 'AK':
        index_num = 1
    else:
        index_num = 0
    if household_size < 9:
        return 100.0 * household_income/(0.5*poverty['level'][household_size][index_num])
    #sys.stderr.write("poverty_percentage end\n")
    return 100.0 * household_income/(0.5*(poverty['level'][8][index_num] + poverty['level']['extra'][index_num] * (household_size - 8)))

def service_areas():
    #sys.stderr.write("service_areas start\n")
    redis = DARedis()
    result = redis.get('lsc_service_areas')
    if result is None:
        #sys.stderr.write('service_areas: calling arcgis.\n')
        r = requests.get('https://services3.arcgis.com/n7h3cEoHTyNCwjCf/ArcGIS/rest/services/BasicFieldServiceAreas_GrantCycle/FeatureServer/0/query?where=OBJECTID%3E%3D0&objectIds=&time=&geometry=&geometryType=esriGeometryEnvelope&inSR=&spatialRel=esriSpatialRelIntersects&resultType=none&distance=0.0&units=esriSRUnit_Meter&returnGeodetic=false&outFields=*&returnGeometry=false&returnCentroid=false&multipatchOption=xyFootprint&maxAllowableOffset=&geometryPrecision=&outSR=&datumTransformation=&applyVCSProjection=false&returnIdsOnly=false&returnUniqueIdsOnly=false&returnCountOnly=false&returnExtentOnly=false&returnQueryGeometry=false&returnDistinctValues=false&orderByFields=&groupByFieldsForStatistics=&outStatistics=&having=&resultOffset=&resultRecordCount=&returnZ=false&returnM=false&returnExceededLimitFeatures=true&quantizationParameters=&sqlFormat=none&f=pjson&token=')
        if r.status_code != 200:
            redis.set('lsc_service_areas', '{}')
            sys.stderr.write('load_service_areas: got error code {} from ArcGIS.  Response: {}\n'.format(r.status_code, r.text))
        else:
            try:
                the_dict = r.json()
                assert 'features' in the_dict
                assert len(the_dict['features']) > 0
                redis.set('lsc_service_areas', r.text)
            except Exception as the_err:
                redis.set('lsc_service_areas', '{}')
                sys.stderr.write('load_service_areas: got invalid response from server: {}\n'.format(text_type(the_err)))
        redis.expire('lsc_service_areas', 60*60*24*7)
        result = redis.get('lsc_service_areas')
    #sys.stderr.write("service_areas end\n")
    return json.loads(result.decode())

def load_program_data():
    #sys.stderr.write("load_program_data start\n")
    (path, mimetype) = path_and_mimetype('docassemble.lscrefer:data/sources/Programs.json')
    with open(path, 'rU', encoding='utf-8') as fp:
        program_list = json.load(fp)
    lsc_programs.clear()
    for program_dict in program_list:
        program = dict()
        lsc_programs[program_dict["Serv_Area_ID"]] = program
        program['name'] = program_dict["R_Legalname"].strip()
        program['phone_number'] = program_dict["Local_800"].strip()
        program['url'] = program_dict["Web_URL"].strip()
    lsc_programs_by_rin.clear()
    lsc_programs_by_serv_a.clear()
    area_data = service_areas()
    if 'features' not in area_data:
        sys.stderr.write("area data is empty\n")
    else:
        for item in area_data['features']:
            attribs = item['attributes']
            if attribs['ServArea'] == 'MA-4':
                attribs['ServArea'] = 'MA04'
                attribs['ServArea_1'] = 'MA-4'
                attribs['servA'] = 'MA04'
            service_area = attribs['ServArea_1'].strip()
            if service_area in lsc_programs:
                lsc_programs_by_rin[attribs['RIN']] = lsc_programs[service_area]
                lsc_programs_by_serv_a[attribs['servA']] = lsc_programs[service_area]
                lsc_programs[service_area]['rin'] = attribs['RIN']
                lsc_programs[service_area]['serv_a'] = attribs['servA']
            else:
                sys.stderr.write("Could not find {} in program info.\n".format(service_area))
    #sys.stderr.write("load_program_data end\n")

def offices_for(org, by_proximity_to=None):
    #sys.stderr.write("offices_for start\n")
    if org is None:
        #sys.stderr.write("offices_for end None\n")
        return None
    params = copy.copy(office_base_params)
    params['where'] = "recipID={}".format(org.rin)
    r = requests.get(office_base_url, params=params)
    if r.status_code != 200:
        #sys.stderr.write("offices_for end exception\n")
        raise Exception('offices_for: got error code {} from ArcGIS.  Response: {}'.format(r.status_code, r.text))
    result = r.json()
    offices = DAList(object_type=Address)
    offices.set_random_instance_name()
    for office_data in result['features']:
        attribs = office_data['attributes']
        office = offices.appendObject()
        office.address = attribs['address'].strip()
        office.city = attribs['City'].strip()
        office.state = attribs['State'].strip()
        office.zip = attribs['ZIP'].strip()
        office.location.longitude = attribs['Longitude']
        office.location.latitude = attribs['Latitude']
        office.office_type = attribs['officetype'].strip()
        if attribs['bldgSuite']:
            office.unit = attribs['bldgSuite'].strip()
        if by_proximity_to:
            office.distance = distance_between(by_proximity_to.address, office)
    offices.gathered = True
    if by_proximity_to:
        by_proximity_to.address.geolocate()
        if not by_proximity_to.address.geolocate_success:
            raise Exception('offices_for: failure to geolocate address')
        offices.elements = sorted(offices.elements, key=lambda y: y.distance)
        offices._reset_instance_names()
    #sys.stderr.write("offices_for end\n")
    return offices

def distance_between(addr1, addr2):
    #sys.stderr.write("distance_between start\n")
    R = 3958.8
    lat1 = radians(addr1.location.latitude)
    lon1 = radians(addr1.location.longitude)
    lat2 = radians(addr2.location.latitude)
    lon2 = radians(addr2.location.longitude)
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat / 2)**2 + cos(lat1) * cos(lat2) * sin(dlon / 2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    #sys.stderr.write("distance_between end\n")
    return R * c

def cities_near(org, person):
    #sys.stderr.write("cities_near start\n")
    offices = offices_for(org)
    person.address.geolocate()
    if not person.address.geolocate_success:
        raise Exception('cities_near: failure to geolocate address')
    cities = DAList(gathered=True)
    cities.set_random_instance_name()
    for y in sorted(offices, key=lambda y: distance_between(person.address, y)):
        if y.city not in cities:
            cities.append(y.city)
    cities.gathered = True
    #sys.stderr.write("cities_near end\n")
    return cities

def lsc_program_for(person):
    #sys.stderr.write("lsc_program_for start\n")
    #sys.stderr.write("doing geolocate\n")
    person.address.geolocate()
    #sys.stderr.write("did geolocate\n")
    if not person.address.geolocate_success:
        raise Exception('lsc_program_for: failure to geolocate address')
    params = copy.copy(base_params)
    params['geometry'] = "{},{}".format(person.address.location.longitude, person.address.location.latitude)
    #sys.stderr.write("calling %s base_url with %s\n" % (base_url, repr(params)))
    r = requests.get(base_url, params=params, timeout=10)
    #sys.stderr.write("ok done\n")
    if r.status_code != 200:
        raise Exception('lsc_program_for: got error code {} from ArcGIS.  Response: {}'.format(r.status_code, r.text))
    result = r.json()
    if not isinstance(result, dict) or 'features' not in result or not isinstance(result['features'], list):
        raise Exception('lsc_program_for: unexpected response from server')
    if len(result['features']) == 0:
        return None
    if 'attributes' not in result['features'][0] or not isinstance(result['features'][0]['attributes'], dict) or '':
        raise Exception('lsc_program_for: unexpected response from server')
    attribs = result['features'][0]['attributes']
    if 'Grantee' not in attribs or 'ServArea' not in attribs:
        raise Exception('lsc_program_for: missing information in response')
    service_area = attribs['ServArea'].strip()
    if service_area not in lsc_programs_by_serv_a:
        raise Exception('lsc_program_for: service area {} not found'.format(service_area))
    program = lsc_programs_by_serv_a[service_area]
    result = Organization()
    result.set_random_instance_name()
    result.name.text = program['name']
    result.phone_number = program['phone_number']
    result.url = program['url']
    if 'rin' in program:
        result.rin = program['rin']
    if 'serv_a' in program:
        result.serv_a = program['rin']
    #sys.stderr.write("lsc_program_for end\n")
    return result

load_program_data()
