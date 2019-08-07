FROM python:3-slim
MAINTAINER Graham Moore "graham.moore@sesam.io"
COPY ./service /service
COPY ./xml2json /xml2json
RUN apt-get update && apt-get install -y g++
WORKDIR /xml2json
RUN  g++ -shared -fpic -x c++ ./include/xml2json.hpp -o ../service/xml2json.so
WORKDIR /service
RUN pip install -r requirements.txt
EXPOSE 5000/tcp
ENTRYPOINT ["python"]
CMD ["xml-translator-service.py"]
