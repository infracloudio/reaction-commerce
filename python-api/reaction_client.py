import requests
import json
import yaml
import sys
from simplecrypt import decrypt


def load_yaml(path):
    with open(path, 'r') as config_file:
        return yaml.load(config_file)


def decrypt_password(key):
    with open("python-api/secret.txt", 'r') as pfile:
        return decrypt(key, pfile.read())


def set_environment_values(data, email, password, host_url,
                           controller_flag=False):
    if controller_flag:
        data['spec']['template']['spec']['containers'][0]['env'][
            0]['value'] = "{0}:30822".format(host_url)
        data['spec']['template']['spec']['containers'][0]['env'][
            1]['value'] = "mongodb://localhost:27017/reaction"
        data['spec']['template']['spec']['containers'][0]['env'][
            2]['value'] = 'smtp://{0}:{1}@smtp.gmail.com:465'.format(email,
                                                                     password)
        data['spec']['template']['spec']['containers'][0]['env'][
            3]['value'] = 'admin'
        data['spec']['template']['spec']['containers'][0]['env'][
            4]['value'] = password
        data['spec']['template']['spec']['containers'][0]['env'][
            5]['value'] = email
        data['spec']['template']['spec']['containers'][0]['ports'][
            0]['containerPort'] = 80
    else:
        data['spec']['ports'][0]['port'] = 80
        data['spec']['ports'][0]['targetPort'] = 80
    return data


def get_auth():
    creds_data = load_yaml("python-api/details.yaml")
    access_key = creds_data['access_key']
    password = decrypt_password(creds_data['decrypt_key'])
    return (access_key, password)


def set_headers(headers, rancher_url):
    headers['Host'] = rancher_url.split("//")[1]
    headers['Origin'] = rancher_url
    return headers


def send_request(url, payload, headers, auth):
    response = requests.post(url, json.dumps(payload),
                             headers=headers, auth=auth)
    assert response.status_code in range(200, 210)
    print "Response: {0}\n".format(response.json())


def create_controller(url, headers, controller_data, auth):
    print "Creating reaction controller"
    print "RC Payload: "+json.dumps(controller_data)
    send_request(url, controller_data, headers, auth)


def create_service(url, headers, service_data, auth):
    print "Creating reaction service"
    print "RS Payload: "+json.dumps(service_data)
    send_request(url, service_data, headers, auth)


def get_cloud_details(rancher_cloud):
    data = load_yaml("python-api/details.yaml")
    return data[rancher_cloud]

if __name__ == "__main__":
    rancher_url = sys.argv[1]
    host_url = sys.argv[2]
    email = sys.argv[3]
    password = sys.argv[4]
    rancher_cloud = sys.argv[5]

    cloud_details = get_cloud_details(rancher_cloud)
    account_id = cloud_details['account_id']

    referer = "{0}/env/{1}/kubernetes/apply?kind=".format(rancher_url,
                                                          account_id)
    url = "{0}/r/projects/{1}/kubectld:8091/".format(rancher_url, account_id)
    url += "v1-kubectl/create?defaultNamespace=default"
    auth = get_auth()

    service_data = load_yaml("0/reaction-service.yml")
    service_data = set_environment_values(service_data, email,
                                          password, host_url)

    controller_data = load_yaml("0/reaction-controller.yml")
    controller_data = set_environment_values(controller_data, email, password,
                                             host_url, True)

    headers = set_headers(cloud_details['headers'], rancher_url)

    headers['Referer'] = referer+"ReplicationController"
    create_controller(url, headers, controller_data, auth)

    headers['Referer'] = referer+"Service"
    create_service(url, headers, service_data, auth)
