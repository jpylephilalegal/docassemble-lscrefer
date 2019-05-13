import requests
import copy
import json
import re
import sys
from six import text_type
from io import open
from docassemble.base.util import Person, DADict, path_and_mimetype, DARedis, DAList, Address, objects_from_file
from math import sin, cos, sqrt, atan2, radians

__all__ = ['service_area_for', 'offices_for', 'cities_near', 'poverty_percentage']

base_url = "https://services3.arcgis.com/n7h3cEoHTyNCwjCf/ArcGIS/rest/services/BasicField_ServiceAreas2019/FeatureServer/0/query"
base_params = {'where': 'OBJECTID>=0', 'objectIds': '', 'time': '', 'geometryType': 'esriGeometryPoint', 'inSR': '{"wkid": 4326}', 'spatialRel': 'esriSpatialRelWithin', 'resultType': 'none', 'distance': '0.0', 'units': 'esriSRUnit_Meter', 'returnGeodetic': 'false', 'outFields': '*', 'returnGeometry': 'false', 'returnCentroid': 'false', 'multipatchOption': 'xyFootprint', 'maxAllowableOffset': '', 'geometryPrecision': '', 'outSR': '{"wkid": 4326}', 'datumTransformation': '', 'applyVCSProjection': 'false', 'returnIdsOnly': 'false', 'returnUniqueIdsOnly': 'false', 'returnCountOnly': 'false', 'returnExtentOnly': 'false', 'returnQueryGeometry': 'false', 'returnDistinctValues': 'false', 'orderByFields': '', 'groupByFieldsForStatistics': '', 'outStatistics': '', 'having': '', 'resultOffset': '', 'resultRecordCount': '', 'returnZ': 'false', 'returnM': 'false', 'returnExceededLimitFeatures': 'true', 'quantizationParameters': '', 'sqlFormat': 'none', 'f': 'pjson', 'token': ''}

office_base_url = "https://services3.arcgis.com/n7h3cEoHTyNCwjCf/ArcGIS/rest/services/LSC_offices_grantees_main_branch_(Public)/FeatureServer/0/query"
office_base_params = {'objectIds': '', 'time': '', 'geometry': '', 'geometryType': 'esriGeometryEnvelope', 'inSR': '', 'spatialRel': 'esriSpatialRelIntersects', 'resultType': 'none', 'distance': '0.0', 'units': 'esriSRUnit_Meter', 'returnGeodetic': 'false', 'outFields': '*', 'returnGeometry': 'false', 'multipatchOption': 'xyFootprint', 'maxAllowableOffset': '', 'geometryPrecision': '', 'outSR': '', 'datumTransformation': '', 'applyVCSProjection': 'false', 'returnIdsOnly': 'false', 'returnUniqueIdsOnly': 'false', 'returnCountOnly': 'false', 'returnExtentOnly': 'false', 'returnQueryGeometry': 'false', 'returnDistinctValues': 'false', 'orderByFields': '', 'groupByFieldsForStatistics': '', 'outStatistics': '', 'having': '', 'resultOffset': '', 'resultRecordCount': '', 'returnZ': 'false', 'returnM': 'false', 'returnExceededLimitFeatures': 'true', 'quantizationParameters': '', 'sqlFormat': 'none', 'f': 'pjson', 'token': ''}

lsc_programs = dict()
lsc_programs_by_rin = dict()
lsc_programs_by_serv_a = dict()

poverty = objects_from_file("docassemble.lscrefer:data/sources/poverty.yml")

def poverty_percentage(household_income, household_size, state):
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
    return 100.0 * household_income/(0.5*(poverty['level'][8][index_num] + poverty['level']['extra'][index_num] * (household_size - 8)))

def service_areas():
    redis = DARedis()
    result = redis.get('lsc_service_areas')
    if result is None:
        sys.stderr.write('service_areas: calling arcgis.\n')
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
    return json.loads(result.decode())

def load_program_data():
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
            service_area = attribs['ServArea_1'].strip()
            if service_area in lsc_programs:
                lsc_programs_by_rin[attribs['RIN']] = lsc_programs[service_area]
                lsc_programs_by_serv_a[attribs['servA']] = lsc_programs[service_area]
                lsc_programs[service_area]['rin'] = attribs['RIN']
                lsc_programs[service_area]['serv_a'] = attribs['servA']
            else:
                sys.stderr.write("Could not find {} in program info.\n".format(service_area))

def offices_for(org):
    if org is None:
        return None
    params = copy.copy(office_base_params)
    params['where'] = "recipID={}".format(org.rin)
    r = requests.get(office_base_url, params=params)
    if r.status_code != 200:
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
    offices.gathered = True
    return offices

def distance_between(addr1, addr2):
    R = 3958.8
    lat1 = radians(addr1.location.latitude)
    lon1 = radians(addr1.location.longitude)
    lat2 = radians(addr2.location.latitude)
    lon2 = radians(addr2.location.longitude)
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat / 2)**2 + cos(lat1) * cos(lat2) * sin(dlon / 2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return R * c

def cities_near(org, person):
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
    return cities

def service_area_for(person):
    person.address.geolocate()
    if not person.address.geolocate_success:
        raise Exception('service_area_for: failure to geolocate address')
    params = copy.copy(base_params)
    params['geometry'] = "{},{}".format(person.address.location.longitude, person.address.location.latitude)
    r = requests.get(base_url, params=params)
    if r.status_code != 200:
        raise Exception('service_area_for: got error code {} from ArcGIS.  Response: {}'.format(r.status_code, r.text))
    result = r.json()
    if not isinstance(result, dict) or 'features' not in result or not isinstance(result['features'], list):
        raise Exception('service_area_for: unexpected response from server')
    if len(result['features']) == 0:
        return None
    if 'attributes' not in result['features'][0] or not isinstance(result['features'][0]['attributes'], dict) or '':
        raise Exception('service_area_for: unexpected response from server')
    attribs = result['features'][0]['attributes']
    if 'Grantee' not in attribs or 'ServArea' not in attribs:
        raise Exception('service_area_for: missing information in response')
    service_area = attribs['ServArea'].strip()
    if service_area not in lsc_programs_by_serv_a:
        raise Exception('service_area_for: service area {} not found'.format(service_area))
    program = lsc_programs_by_serv_a[service_area]
    result = Person()
    result.set_random_instance_name()
    result.name.text = program['name']
    result.phone_number = program['phone_number']
    result.url = program['url']
    if 'rin' in program:
        result.rin = program['rin']
    if 'serv_a' in program:
        result.serv_a = program['rin']
    return result

load_program_data()
