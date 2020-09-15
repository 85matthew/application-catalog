#!/usr/bin/env python

##################################################
## Tool to manage add/delete users to the Istio 101 Workshop
##################################################
## Author: mwilkers@redhat.com
## Maintainer: Rhg-aws-mgmt@redhat.com
##################################################

import argparse
import os
import sys
import pathlib
import subprocess
import yaml
import shutil
import shlex


# Parse args
parser = argparse.ArgumentParser()
parser.add_argument("action", type=str, help='action to take (add or remove)')
parser.add_argument("username", type=str, nargs='?', help='username to take action on')
parser.add_argument("password", type=str, nargs='?', help='password for user(s)')
parser.add_argument("--count", type=int, nargs='?', help='count for actions against sequenced users')
parser.add_argument("--start", type=int, nargs='?', help='count for actions against sequenced users')
parser.add_argument("--workshopname", type=str, required=True, help='unique name for workshop')
args = parser.parse_args()

# Global Vars

SCRIPT_DIR = pathlib.Path(__file__).parent.absolute()
BASE_REPO_PATH = SCRIPT_DIR.parent.absolute()

BASE_WORKSHOP_DIRECTORIES = ["user-ingress-gateway", "user_operator_group", "user_projects", "user_subscriptions"]

BASE_WORKSHOP_FULL_PATH =  f'{BASE_REPO_PATH}/overlays/{args.workshopname}'
WORKSHOP_GROUP_FILE_FULL_PATH = f'{BASE_WORKSHOP_FULL_PATH}/group.yaml'
SERVICE_MESH_MEMBER_ROLE_FILE_FULL_PATH = f'{BASE_WORKSHOP_FULL_PATH}/service-mesh-member-role.yaml'
USER_MEMBER_ROLE_FILE_FULL_PATH = f'{BASE_WORKSHOP_FULL_PATH}/member_role.yaml'
USER_PROJECTS_DIR_FULL_PATH = f'{BASE_WORKSHOP_FULL_PATH}/user_projects'
USER_SUBSCRIPTIONS_DIR_FULL_PATH = f'{BASE_WORKSHOP_FULL_PATH}/user_subscriptions'
USER_INGRESS_GATWAYS_DIR_FULL_PATH = f'{BASE_WORKSHOP_FULL_PATH}/user-ingress-gateway'
USER_OPERATOR_GROUP_DIR_FULL_PATH = f'{BASE_WORKSHOP_FULL_PATH}/user_operator_group'


# Kustomize Files
kustomize_files = {
    f'{BASE_WORKSHOP_FULL_PATH}/kustomization.yaml' : None,
    f'{USER_INGRESS_GATWAYS_DIR_FULL_PATH}/kustomization.yaml' : None,
    f'{USER_OPERATOR_GROUP_DIR_FULL_PATH}/kustomization.yaml' : None,
    f'{USER_SUBSCRIPTIONS_DIR_FULL_PATH}/kustomization.yaml' : None,
    f'{USER_PROJECTS_DIR_FULL_PATH}/kustomization.yaml' : None
}

# Manifest files to be edited.
edit_files_list = kustomize_files
edit_files_list[WORKSHOP_GROUP_FILE_FULL_PATH] : None
edit_files_list[SERVICE_MESH_MEMBER_ROLE_FILE_FULL_PATH] : None

command = {}
users = []


def validate_ocp_logged_in():
    cmd = "oc whoami"
    args = shlex.split(cmd)
    result = subprocess.run(args, stdout=subprocess.PIPE )

    if result.returncode != 0:
        print("Please make sure you are logged into OpenShift")
        sys.exit(1)

def validate_input(args):
    if args.action == "add" or args.action == "delete":
        if len(args.username) > 0:
            if args.count == None:
                # Run user stuff
                print("Validated: add single user")
            else:
                # Run as prefix+count
                print("Validated: add user sequence")
    elif args.action == "save":
        print("Saving")
    elif args.action == "init":
        print("Initializing")
    elif args.action == "get":
        print("Retrieving")
    else:
        raise argparse.ArgumentTypeError("Wrong value")


def init_workshop_group(workshopname):

    if input("This will overwrite any existing configuration. Are you sure? (y/n) ") != "y":
        exit()
    if input("Really sure? (y/n) ") != "y":
        exit()

    workshop_group = f"""
apiVersion: user.openshift.io/v1
kind: Group
metadata:
  name: {workshopname}-workshop
spec:
  members:
"""

    sm_member_roll = f"""
apiVersion: maistra.io/v1
kind: ServiceMeshMemberRoll
metadata:
  name: default
  namespace: istio-system
spec:
  members:
"""

    empty_kustomize_file = f"""
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
"""

    workshop_kustomize_file = f"""
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

resources:
  - user-ingress-gateway
  - user_operator_group
  - user_projects
  - user_subscriptions
  - group.yaml
  - service-mesh-member-role.yaml
"""

    edit_files_list[f'{WORKSHOP_GROUP_FILE_FULL_PATH}'] = workshop_group
    edit_files_list[f'{SERVICE_MESH_MEMBER_ROLE_FILE_FULL_PATH}'] = sm_member_roll
    edit_files_list[f'{BASE_WORKSHOP_FULL_PATH}/kustomization.yaml'] = workshop_kustomize_file
    edit_files_list[f'{USER_INGRESS_GATWAYS_DIR_FULL_PATH}/kustomization.yaml'] = empty_kustomize_file
    edit_files_list[f'{USER_OPERATOR_GROUP_DIR_FULL_PATH}/kustomization.yaml'] = empty_kustomize_file
    edit_files_list[f'{USER_SUBSCRIPTIONS_DIR_FULL_PATH}/kustomization.yaml'] = empty_kustomize_file
    edit_files_list[f'{USER_PROJECTS_DIR_FULL_PATH}/kustomization.yaml'] = empty_kustomize_file


# Initialize workshop dirs
    shutil.rmtree(f'{WORKSHOP_GROUP_FILE_FULL_PATH}', ignore_errors=True)
    os.makedirs(os.path.dirname(f'{WORKSHOP_GROUP_FILE_FULL_PATH}'), exist_ok=True)

    for dir in BASE_WORKSHOP_DIRECTORIES:
        print(dir)
        shutil.rmtree(f'{BASE_WORKSHOP_FULL_PATH}/{dir}/', ignore_errors=True)
        os.makedirs(os.path.dirname(f'{BASE_WORKSHOP_FULL_PATH}/{dir}/'), exist_ok=True)

    for key, value in edit_files_list.items():
        print(key, ":", value)
        write_to_file(key, value)

    edit_kustomize("add", f'{args.workshopname}', f'{BASE_WORKSHOP_FULL_PATH}')

def write_to_file(file_path, content):
    f = open(f'{file_path}', "w")
    f.write(content)
    f.close()


def add_user_to_manifest(username, manifest):
    user_list = list()

    f =  open(f'{manifest}', "r")
    data = f.read()
    f.close()
    ydoc = yaml.load(data, Loader=yaml.FullLoader)
    if ydoc['spec']["members"] != None:
        user_list = list(ydoc['spec']["members"])

    user_list.append(username)
    ydoc['spec']["members"] = user_list

    f =  open(f'{manifest}', "w")
    f.write(yaml.dump(ydoc))
    f.close()


def remove_user_from_manifest(username, manifest):
    user_list = list()

    f =  open(f'{manifest}', "r")
    data = f.read()
    f.close()
    ydoc = yaml.load(data, Loader=yaml.FullLoader)
    if ydoc['spec']["members"] != None:
        user_list = list(ydoc['spec']["members"])

    user_list.remove(username)
    ydoc['spec']["members"] = user_list

    f =  open(f'{manifest}', "w")
    f.write(yaml.dump(ydoc))
    f.close()


def create_user_project(workshop, username):

    template = f"""
apiVersion: project.openshift.io/v1
kind: Project
metadata:
  annotations:
    openshift.io/requester: {workshop}-{username}
  name: {workshop}-{username}
spec:
  finalizers:
  - kubernetes
"""

    template2 = f"""
apiVersion: operators.coreos.com/v1
kind: OperatorGroup
metadata:
  name: {workshop}-{username}
  namespace: {workshop}-{username}
spec:
  targetNamespaces:
  - {workshop}-{username}
"""


    f = open(f'{USER_PROJECTS_DIR_FULL_PATH}/{username}.yaml', "w")
    f.write(template)
    f.close()
    edit_kustomize("add", f'{username}.yaml', f'{USER_PROJECTS_DIR_FULL_PATH}')
    f2 = open(f'{USER_OPERATOR_GROUP_DIR_FULL_PATH}/{username}.yaml', "w")
    f2.write(template2)
    f2.close()
    edit_kustomize("add", f'{username}.yaml', f'{USER_OPERATOR_GROUP_DIR_FULL_PATH}')

def remove_manifests(workshop, username):
    print(kustomize_files)
    for key, value in kustomize_files.items():
        edit_kustomize("remove", f'{username}.yaml', key)

    os.remove(f'{USER_PROJECTS_DIR_FULL_PATH}/{username}.yaml')
    os.remove(f'{USER_SUBSCRIPTIONS_DIR_FULL_PATH}/{username}.yaml')
    os.remove(f'{USER_INGRESS_GATWAYS_DIR_FULL_PATH}/{username}.yaml')
    os.remove(f'{USER_OPERATOR_GROUP_DIR_FULL_PATH}/{username}.yaml')


def install_keycloak_operator(workshop, username):

    template = f"""
apiVersion: operators.coreos.com/v1alpha1
kind: Subscription
metadata:
  name: keycloak-operator
  namespace: {workshop}-{username}
spec:
  channel: alpha
  installPlanApproval: Manual
  name: keycloak-operator
  source: community-operators
  sourceNamespace: openshift-marketplace
  startingCSV: keycloak-operator.v10.0.0
"""

    f = open(f'{USER_SUBSCRIPTIONS_DIR_FULL_PATH}/{username}.yaml', "w")
    f.write(template)
    f.close()


def delete_all_user_projects(username, usercount):

    os.chdir(USER_PROJECTS_DIR_FULL_PATH)
    os.remove(f'{USER_PROJECTS_DIR_FULL_PATH}/*.yaml')


def create_user_ingress_gateway(workshop, username):
    namespace = f'{workshop}-{username}'
    template = f"""
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  namespace: {namespace}
  name: istio-demogateway-{username}
spec:
  podSelector:
    matchLabels:
      istio: demogateway-{username}
  policyTypes:
  - Ingress
---
apiVersion: v1
kind: ServiceAccount
metadata:
  namespace: {namespace}
  name: demogateway-{username}-service-account
  labels:
    app: istio-demogateway-{username}
    istio: demogateway-{username}
---
apiVersion: v1
kind: Service
metadata:
  namespace: {namespace}
  annotations:
    maistra.io/mesh-generation: 1.0.7-1.el8-1
  labels:
    app: istio-demogateway-{username}
    app.kubernetes.io/component: gateways
    app.kubernetes.io/instance: istio-system
    app.kubernetes.io/managed-by: maistra-istio-operator
    app.kubernetes.io/name: gateways
    app.kubernetes.io/part-of: istio
    app.kubernetes.io/version: 1.0.7-1.el8-1
    chart: gateways
    heritage: Tiller
    istio: demogateway-{username}
    maistra-version: 1.0.7
    maistra.io/owner: istio-system
    release: istio
  name: istio-demogateway-{username}
spec:
  ports:
  - name: status-port
    port: 15020
    protocol: TCP
    targetPort: 15020
  - name: http2
    port: 80
    protocol: TCP
    targetPort: 8080
  - name: https
    port: 443
    protocol: TCP
    targetPort: 8443
  - name: tls
    port: 15443
    protocol: TCP
    targetPort: 15443
  selector:
    app: istio-demogateway-{username}
    istio: demogateway-{username}
    release: istio
  sessionAffinity: None
  type: ClusterIP
---
apiVersion: apps/v1
kind: Deployment
metadata:
  namespace: {namespace}
  annotations:
    deployment.kubernetes.io/revision: "1"
    maistra.io/mesh-generation: 1.0.7-1.el8-1
  generation: 1
  labels:
    app: istio-demogateway-{username}
    app.kubernetes.io/component: gateways
    app.kubernetes.io/instance: istio-system
    app.kubernetes.io/managed-by: maistra-istio-operator
    app.kubernetes.io/name: gateways
    app.kubernetes.io/part-of: istio
    app.kubernetes.io/version: 1.0.7-1.el8-1
    chart: gateways
    heritage: Tiller
    istio: demogateway-{username}
    maistra-version: 1.0.7
    maistra.io/owner: istio-system
    release: istio
  name: istio-demogateway-{username}
spec:
  progressDeadlineSeconds: 2147483647
  replicas: 1
  revisionHistoryLimit: 2147483647
  selector:
    matchLabels:
      app: istio-demogateway-{username}
      istio: demogateway-{username}
  strategy:
    rollingUpdate:
      maxSurge: 25%
      maxUnavailable: 25%
    type: RollingUpdate
  template:
    metadata:
      annotations:
        sidecar.istio.io/inject: "false"
      creationTimestamp: null
      labels:
        app: istio-demogateway-{username}
        chart: gateways
        heritage: Tiller
        istio: demogateway-{username}
        maistra-control-plane: istio-system
        release: istio
    spec:
      affinity:
        nodeAffinity:
          preferredDuringSchedulingIgnoredDuringExecuion:
          - preference:
              matchExpressions:
              - key: beta.kubernetes.io/arch
                operator: In
                values:
                - amd64
            weight: 2
          - preference:
              matchExpressions:
              - key: beta.kubernetes.io/arch
                operator: In
                values:
                - ppc64le
            weight: 2
          - preference:
              matchExpressions:
              - key: beta.kubernetes.io/arch
                operator: In
                values:
                - s390x
            weight: 2
          requiredDuringSchedulingIgnoredDuringExecuton:
            nodeSelectorTerms:
            - matchExpressions:
              - key: beta.kubernetes.io/arch
                operator: In
                values:
                - amd64
                - ppc64le
                - s390x
      containers:
      - args:
        - proxy
        - router
        - --domain
        - {username}.svc.cluster.local
        - --log_output_level=default:info
        - --drainDuration
        - 45s
        - --parentShutdownDuration
        - 1m0s
        - --connectTimeout
        - 10s
        - --serviceCluster
        - ingress-user{username}
        - --zipkinAddress
        - zipkin.istio-system:9411
        - --proxyAdminPort
        - "15000"
        - --statusPort
        - "15020"
        - --controlPlaneAuthPolicy
        - NONE
        - --discoveryAddress
        - istio-pilot.istio-system:15010
        env:
        - name: POD_NAME
          valueFrom:
            fieldRef:
              apiVersion: v1
              fieldPath: metadata.name
        - name: POD_NAMESPACE
          valueFrom:
            fieldRef:
              apiVersion: v1
              fieldPath: metadata.namespace
        - name: INSTANCE_IP
          valueFrom:
            fieldRef:
              apiVersion: v1
              fieldPath: status.podIP
        - name: HOST_IP
          valueFrom:
            fieldRef:
              apiVersion: v1
              fieldPath: status.hostIP
        - name: ISTIO_META_POD_NAME
          valueFrom:
            fieldRef:
              apiVersion: v1
              fieldPath: metadata.name
        - name: ISTIO_META_CONFIG_NAMESPACE
          valueFrom:
            fieldRef:
              apiVersion: v1
              fieldPath: metadata.namespace
        - name: ISTIO_META_ROUTER_MODE
          value: sni-dnat
        image: registry.redhat.io/openshift-service-mesh/proxyv2-rhel8:1.0.7
        imagePullPolicy: IfNotPresent
        name: istio-proxy
        ports:
        - containerPort: 15020
          name: status-port
          protocol: TCP
        - containerPort: 8080
          name: http2
          protocol: TCP
        - containerPort: 8443
          name: https
          protocol: TCP
        - containerPort: 15443
          name: tls
          protocol: TCP
        - containerPort: 15090
          name: http-envoy-prom
          protocol: TCP
        readinessProbe:
          failureThreshold: 30
          httpGet:
            path: /healthz/ready
            port: 15020
            scheme: HTTP
          initialDelaySeconds: 1
          periodSeconds: 2
          successThreshold: 1
          timeoutSeconds: 1
        resources:
          requests:
            cpu: 10m
            memory: 128Mi
        terminationMessagePath: /dev/termination-log
        terminationMessagePolicy: File
        volumeMounts:
        - mountPath: /etc/certs
          name: istio-certs
          readOnly: true
        - mountPath: /etc/istio/ingressgateway-certs
          name: ingressgateway-certs
          readOnly: true
        - mountPath: /etc/istio/ingressgateway-ca-erts
          name: ingressgateway-ca-certs
          readOnly: true
      dnsPolicy: ClusterFirst
      restartPolicy: Always
      schedulerName: default-scheduler
      serviceAccount: demogateway-{username}-service-account
      serviceAccountName: demogateway-{username}-service-account
      terminationGracePeriodSeconds: 30
      volumes:
      - name: istio-certs
        secret:
          defaultMode: 420
          optional: true
          secretName: istio.demogateway-{username}-service-account
      - name: ingressgateway-certs
        secret:
          defaultMode: 420
          optional: true
          secretName: istio-ingressgateway-certs
      - name: ingressgateway-ca-certs
        secret:
          defaultMode: 420
          optional: true
          secretName: istio-ingressgateway-ca-certs
---
apiVersion: route.openshift.io/v1
kind: Route
metadata:
  namespace: {namespace}
  annotations:
    openshift.io/host.generated: "true"
  labels:
    app: istio-demogateway-{username}
    app.kubernetes.io/component: gateways
    app.kubernetes.io/instance: istio-system
    app.kubernetes.io/managed-by: maistra-istio-operator
    app.kubernetes.io/name: gateways
    app.kubernetes.io/part-of: istio
    app.kubernetes.io/version: 1.0.7-1.el8-1
    chart: gateways
    heritage: Tiller
    istio: demogateway-{username}
    maistra-version: 1.0.7
    maistra.io/owner: istio-system
    release: istio
  name: istio-demogateway-user{{ item }}
spec:
  port:
    targetPort: 8080
  subdomain: ""
  to:
    kind: Service
    name: istio-demogateway-user{{ item }}
    weight: 100
  wildcardPolicy: None
"""

    f = open(f'{USER_INGRESS_GATWAYS_DIR_FULL_PATH}/{username}.yaml', "w")
    f.write(template)
    f.close()


def add_user(workshopname, username):
    add_user_to_manifest(username, WORKSHOP_GROUP_FILE_FULL_PATH)
    add_user_to_manifest(username, SERVICE_MESH_MEMBER_ROLE_FILE_FULL_PATH)
    create_user_project(workshopname, username)
    install_keycloak_operator(workshopname, username)
    create_user_ingress_gateway(workshopname, username)
    for key, value in kustomize_files.items():
        edit_kustomize("add", f'{username}.yaml', key)


def remove_user(workshopname, username):
    remove_user_from_manifest(username, WORKSHOP_GROUP_FILE_FULL_PATH)
    remove_user_from_manifest(username, SERVICE_MESH_MEMBER_ROLE_FILE_FULL_PATH)
    remove_manifests(workshopname, username)
    for key, value in kustomize_files.items():
        edit_kustomize("remove", f'{username}.yaml', key)
    # for key, value in edit_files_list.items():
    #     edit_kustomize("remove", f'{username}.yaml', key)


def edit_kustomize(action, filename, k_file):

    print(type(k_file))
    print(k_file)
    # for key, value in manifest_files.items():
    dir = os.path.dirname(k_file)
    os.chdir(dir)
    cmd = f"kustomize edit {action} resource {filename}"
    print(cmd)
    args = shlex.split(cmd)
    try:
        result = subprocess.run(args, stdout=subprocess.PIPE )
    except:
        print("Admin permissions don't exist: <continuing>")


def main():
    validate_input(args)
    validate_ocp_logged_in()

    if args.start is not None:
        start = args.start
    else:
        start = 1

    if args.count is not None:
        if args.start is not None:
            count = args.start + args.count
        else:
            count = args.count + 1

    if args.action == "init":
        print("Initializing workshop ...")
        init_workshop_group(args.workshopname)

    elif args.action == "add":
        if len(args.username) > 0 and args.count == None:
            # Call username stuff
            add_user(args.workshopname, args.username)
        else:
            # Call sequence (username + count) stuff
            print("run sequence stuff here")
            for i in range(start, count):
                username = f'{args.username}-{i}'
                print(f'Adding user: {username}')
                add_user(args.workshopname, username)
            print("Done")



    elif args.action == "delete":
        if len(args.username) > 0 and args.count == None:
            # Call username stuff
            remove_user(args.workshopname, args.username)

        else:
            # Call sequence (username + count) stuff
            for i in range(start, count):
                username = f'{args.username}-{i}'
                print(f'Removing user: {username}')
                remove_user(args.workshopname, username)
            print("Done")

    else:
        print("Invalid action")
        sys.exit(1)

if __name__ == "__main__":
    main()
