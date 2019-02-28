from google.cloud import storage
import logging
from flask import abort


# class for reading files from a Google cloud storage
class GoogleCloudStorage:

    # initiate class, the class is taking the path to the file storing the credentials for the Google cloud storage,
    # the credentials itself, and the name of the bucket where the xml files resides as parameters
    def __init__(self, credentialspath, credentials, bucketname):
        # write the content of the credentials to the path specified by credentialspath
        with open(credentialspath, "wb") as out_file:
            out_file.write(credentials.encode())

        self.bucket = bucketname
        pass

    # method for retrieving a list of the files in the Google cloud storage bucket
    def getlistofxmlfiles(self, path):
        def generate():

            # get all the blobs (files) in the bucket
            blobs = bucket.list_blobs()
            # loop through the blogs and only return those in the root folder of the bucket
            for blob in blobs:
                if blob.name.startswith(path) and not blob.name.endswith("/"):  # subfolder object
                    yield blob.name

        try:
            # initiate Google cloud storage client
            storage_client = storage.Client()
            # get the bucket from the Google cloud storage
            bucket = storage_client.get_bucket(self.bucket)

            # return all the files in the bucket
            return generate()
        except Exception as e:
            logging.error(str(e))
            abort(type(e).__name__, str(e))

    # method for downloading the content of a file in the Google cloud storage bucket
    def download(self, filename):
        # initiate Google cloud storage client
        storage_client = storage.Client()
        # get the bucket from the Google cloud storage
        bucket = storage_client.get_bucket(self.bucket)

        try:
            # set chunk size
            chunk_size = 262144 * 4 * 10
            # get the blob from the bucket
            blob = bucket.blob(filename)
            return blob.download_as_string()

        except Exception as e:
            logging.error(str(e))
            abort(type(e).__name__, str(e))