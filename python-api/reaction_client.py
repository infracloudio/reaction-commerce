import requests
import json
import time
import yaml
import sys
from simplecrypt import decrypt


def load_yaml(path):
    with open(path, 'r') as config_file:
        return yaml.load(config_file)


def decrypt_password(key, rancher_cloud):
    if rancher_cloud == "AWS":
        filename = "aws_secret.txt"
    elif rancher_cloud == "DigitalOcean":
        filename = "do_secret.txt"
    with open("python-api/{0}".format(filename), 'r') as pfile:
        return decrypt(key, pfile.read())


def send_request(url, payload, headers, auth):
    print "Url: "+url
    response = requests.post(url, json.dumps(payload),
                             headers=headers, auth=auth)
    print "Response: {0}\n".format(response.json())
    assert response.status_code in range(200, 210)


class ReactionClient():
    def __init__(self, email, password, rancher_cloud):
        self.email = email
        self.password = password
        self.rancher_cloud = rancher_cloud

        data = self.get_rancher_details()
        account_id = data['account_id']
        self.rancher_url = data['rancher_url']
        self.host_url = data['host_url']
        self.auth = self.get_auth(data['access_key'])
        self.headers = data['headers']
        self.referer = "{0}/env/{1}/kubernetes/apply?".format(self.rancher_url,
                                                              account_id)
        self.url = "{0}/r/projects/{1}/".format(self.rancher_url, account_id)
        self.url += "kubectld:8091/v1-kubectl/create?defaultNamespace=default"

    def get_rancher_details(self):
        data = load_yaml("python-api/details.yaml")
        return data[self.rancher_cloud]

    def get_auth(self, access_key):
        creds_data = load_yaml("python-api/details.yaml")
        password = decrypt_password(creds_data['decrypt_key'],
                                    self.rancher_cloud)
        return (access_key, password)

    def set_headers(self):
        self.headers['Host'] = self.rancher_url.split("//")[1]
        self.headers['Origin'] = self.rancher_url

    def start_execution(self):
        self.set_headers()
        self.create_mongo_containers()
        self.create_reaction_containers()

    def create_mongo_containers(self):
        self.create_controllers("0/mongo-controller.yml")
        self.create_services("0/mongo-service.yml")
        print "Waiting for mongo container to start"
        time.sleep(60)

    def create_reaction_containers(self):
        self.create_controllers("0/reaction-controller.yml", True)
        self.create_services("0/reaction-service.yml")

    def create_controllers(self, controller_file, reaction_flag=False):
        controller_data = load_yaml(controller_file)
        if reaction_flag:
            controller_data = self.set_environment_values(controller_data)
        self.set_controller_referer()
        print "Controller Payload: "+json.dumps(controller_data)
        send_request(self.url, controller_data, self.headers, self.auth)

    def create_services(self, service_file):
        service_data = load_yaml(service_file)
        self.set_service_referer()
        print "Service Payload: "+json.dumps(service_data)
        send_request(self.url, service_data, self.headers, self.auth)

    def set_controller_referer(self):
        self.headers['Referer'] = self.referer+"kind=ReplicationController"

    def set_service_referer(self):
        self.headers['Referer'] = self.referer+"kind=Service"

    def set_environment_values(self, data):
        data['spec']['template']['spec']['containers'][0]['env'][
            0]['value'] = "{0}:30822".format(self.host_url)

        mail_url = 'smtp://{0}:{1}@smtp.gmail.com:465'.format(self.email,
                                                              self.password)
        data['spec']['template']['spec']['containers'][0]['env'][
            2]['value'] = mail_url

        data['spec']['template']['spec']['containers'][0]['env'][
            3]['value'] = 'admin'
        data['spec']['template']['spec']['containers'][0]['env'][
            4]['value'] = self.password
        data['spec']['template']['spec']['containers'][0]['env'][
            5]['value'] = self.email
        return data


if __name__ == "__main__":
    email = sys.argv[1]
    password = sys.argv[2]
    rancher_cloud = sys.argv[3]
    reaction_client = ReactionClient(email, password, rancher_cloud)
    reaction_client.start_execution()
