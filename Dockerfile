FROM docker.elastic.co/elasticsearch/elasticsearch:7.17.9

RUN elasticsearch-plugin install --batch https://get.infini.cloud/elasticsearch/analysis-ik/7.17.9
