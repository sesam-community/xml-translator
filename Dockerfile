FROM python:3-slim
MAINTAINER Graham Moore "graham.moore@sesam.io"
COPY ./service /service
COPY ./xml2json /xml2json
RUN apt-get update && apt-get install -y make g++
WORKDIR /xml2json
RUN make
RUN chmod +x /xml2json/xml2json
WORKDIR /service
RUN pip install -r requirements.txt
EXPOSE 5000/tcp
ENTRYPOINT ["python"]
CMD ["xml-translator-service.py"]
