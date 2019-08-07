from os import stat_result

from flask import Flask, request, Response
import json
import time
import os
import logger
import ctypes

from waitress import serve
from googlecloudstorage import GoogleCloudStorage
from dotdictify import Dotdictify

import subprocess
import tempfile

# import ctypes

xml2json_lib = ctypes.cdll.LoadLibrary("./xml2json.so")
xml2json_lib.xml2json_c.argtypes = [ctypes.c_char_p]
xml2json_lib.xml2json_c.restype = ctypes.c_char_p

app = Flask(__name__)
logger = logger.Logger("xml-translator-service")

# the xml files may contain a special attribute that we need to extract
# the structure of the xml is like for instance <EquipmentElevation unit="mm">1</EquipmentElevation>
# when parsing the xml this will be returned as
# "EquipmentElevation": {
#   "unit": "mm",
#   "value": "1"
# }
# the name of the key holding the value can be configured using the special_attr_value_key environmental value
# default value of special_attr_value_key is value
# the name of the special attribute key can be specified using the special_attr_key environmental value
# default value of special_attr_key is unit
special_attr_value_key = os.environ.get("special_attr_value_key", "value")
special_attr_key = os.environ.get("special_attr_key", "unit")

# each xml file will by default start with a Tags-element (root key)
# each entity in the xml file will by default be inside a Tag-element (element key)
# if these two tags changes, they can be configured using the root_key and element_key environment values
root_key = os.environ.get("root_key", "Tags")
element_key = os.environ.get("element_key", "Tag")

# the id field for each element should be determined based on a project mapping file
# this can be changed to use a specific key in the xml element,
# by setting the use_id_key_from_source environment variable to True (default False)
# and specifying the name of the key to use in the id_key_from_source environmental value
# default value for the id_key_from_source is ComosUID
id_key_from_source = os.environ.get("id_key_from_source", "ComosUID")
use_id_key_from_source = os.environ.get("use_id_key_from_source", False)

"""
Google cloud storage requires the environmental variable GOOGLE_APPLICATION_CREDENTIALS for authentication to work
these credentials should be passed to the GOOGLE_APPLICATION_CREDENTIALS_CONTENT environment variable
the GOOGLE_APPLICATION_CREDENTIALS_CONTENT value will be written to the file specified in the
GOOGLE_APPLICATION_CREDENTIALS environment value
the GOOGLE_APPLICATION_BUCKETNAME environment value is used to contain the name of the bucket to read from
"""
credentials = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS_CONTENT")
credentialspath = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
bucketname = os.environ.get("GOOGLE_APPLICATION_BUCKETNAME")

projectname_mapping = json.loads(os.environ.get('project_mapping').replace("'", "\""))
facilitytname_mapping = json.loads(os.environ.get('facility_mapping').replace("'", "\""))


# parse xml and return an ordered dictionary
def parsexml(xml):
    # ctypes approach
    return xml2json_lib.xml2json_c(ctypes.c_char_p(xml))


# determine id of entity, either using a known id from the source or by using projectname mapping
def get_id(entity):
    global projectname_mapping

    if use_id_key_from_source:  # we shall get the id based on a key from the source entity
        new_id = entity[id_key_from_source]
    else:  # we shall get the id based on a projectname mapping
        projectname = entity["ProjectName"]
        for i in projectname_mapping:
            if i["ComosProject"] == entity["ProjectName"]:
                projectname = i["ProjectId"]
        for i in facilitytname_mapping:
            if i["ProjectId"] == projectname and i["ComosFacility"] == entity["FacilityName"]:
                facilityname = i["FacilityName"]
        new_id = projectname + "_" + facilityname + "_" + entity["Label"]

    return new_id


# get the content of the project mapping file and load it into a json structure for future use
def load_projectname_mapping():
    # the project mapping resides in the 'project_id_mapping.json'-file
    mapping_file_path = os.path.abspath("../project_id_mapping.json")
    mappings = open(mapping_file_path).read()

    # load the read project mappings and return it as json
    return json.loads(mappings)


# process entities read from a xml file, adding _id value and remove empty values
def process_entities(entity):
    entity["_id"] = get_id(entity)
    entity["composite_id"] = entity["_id"]
    # removing empty elements in entities
    for key in entity.copy():
        try:
            if (entity[key] is None) or (
                    key in entity and entity[key] is not None and special_attr_value_key not in
                    entity[key] and special_attr_key in entity[key]):
                del entity[key]
        except Exception:
            logger.warn("Failed to remove empty element '%s' from entity with _id '%s'", key,
                        entity[id_key_from_source])
            pass

    return entity


class DataAccess:

    @staticmethod
    def __get_all_xmls(path, args):
        global projectname_mapping
        root_key = args["root_key"]
        element_key = args["element_key"]

        # load projectname mappings
        # projectname_mapping = load_projectname_mapping()

        # initiate Google cloud storage
        google_cloud_storage = GoogleCloudStorage(credentialspath, credentials, bucketname)
        # get xml files from Google cloud storage
        list_of_xml_files = google_cloud_storage.getlistofxmlfiles(path)
        for xml_file_name in list_of_xml_files:
            if not str(xml_file_name).endswith(".xml"):
                continue
            logger.info("Reading '%s'", xml_file_name)
            # parse the content of the xml file into an ordered dict
            start_time = time.time()
            xml_as_byte_string = google_cloud_storage.download(xml_file_name)
            logger.info(
                "File {} downloaded in {} seconds".format(xml_file_name, time.time() - start_time))
            json_str = parsexml(xml_as_byte_string)
            try:
                for entity in Dotdictify(json.loads(json_str.decode("utf-8")))[root_key][element_key]:
                    yield process_entities(entity)
            except KeyError as e:
                logger.error("KeyError occured: {} not found".format(str(e)))
                raise e

    def get_xml(self, path, args):
        # print('getting list')
        return self.__get_all_xmls(path, args)


data_access_layer = DataAccess()


def stream_json(clean):
    first = True
    yield '['
    for i, row in enumerate(clean):
        if not first:
            yield ','
        else:
            first = False
        yield json.dumps(row)
    yield ']'


# main entrypoint of service ('/entities')
@app.route("/<path:path>", methods=["GET"])
def get(path):
    entities = data_access_layer.get_xml(path, args=request.args)
    return Response(
        stream_json(entities),
        mimetype='application/json'
    )


if __name__ == '__main__':
    serve(app, port=int(os.environ.get('PORT', 5000)))
    # app.run(threaded=True, debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
