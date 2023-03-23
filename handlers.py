import kopf
import kubernetes.client
import os
import yaml
import logging
import re

from kubernetes.client.rest import ApiException


@kopf.on.login()
def login_fn(**kwargs):
    return kopf.login_via_client(**kwargs)


@kopf.on.startup()
def configure(settings: kopf.OperatorSettings, **_):
    settings.persistence.finalizer = "namespace-operator/finalizer"
    # Timeout passed along to the Kubernetes API as timeoutSeconds=x
    settings.watching.server_timeout = 300
    # Total number of seconds for a whole watch request per aiohttp:
    # https://docs.aiohttp.org/en/stable/client_reference.html#aiohttp.ClientTimeout.total
    settings.watching.client_timeout = 300
    # Timeout for attempting to connect to the peer per aiohttp:
    # https://docs.aiohttp.org/en/stable/client_reference.html#aiohttp.ClientTimeout.sock_connect
    settings.watching.connect_timeout = 30
    # Wait for that many seconds between watching events
    settings.watching.reconnect_backoff = 1
    # The prefix is prefered instead the key cf https://github.com/nolar/kopf/issues/817
    settings.persistence.diffbase_storage = kopf.AnnotationsDiffBaseStorage(
        prefix="namespace-operator", key="last-handled-configuration"
    )


def get_value(file):
    try:
        with open(file, "r") as ymlfile:
            cfg = yaml.load(ymlfile, Loader=yaml.SafeLoader)
            return cfg
    except Exception:
        return {}


@kopf.on.create("", "v1", "namespaces")
def ns_created(name, logger, **_):
    logger.info(f"Namespace " + name + " is request")

    config = get_value("./config/whitelist.yaml")

    if "whitelist" in config and name in config["whitelist"]:
        logger.info(f"Whitelisted")
        return

    if "whiteregex" in config:
        for regex in config["whiteregex"]:
            x = re.findall(regex, name)
            if len(x) > 0:
                logger.info(f"WhiteRegexed")
                return

    ### NetworkPolicy Part ###
    netPolName = "namespace-operator"
    api_instance = kubernetes.client.NetworkingV1Api()
    netpol_list = api_instance.list_namespaced_network_policy(name)

    try:
        if netPolName not in [item.metadata.name for item in netpol_list.items]:
            logger.info(f"Network Policy must be installed")

            path = os.path.join(os.path.dirname(__file__), "network_policy.yaml")
            text = open(path, "rt").read()
            # text = tmpl.format()
            data = yaml.safe_load(text)

            # create an instance of the API class
            api_instance = kubernetes.client.NetworkingV1Api()
            api_response = api_instance.create_namespaced_network_policy(
                name, data, field_manager="namespace-operator"
            )
            logger.info(
                "NetworkPolicy created for namespace {0} : {1}".format(
                    name, api_response
                )
            )

    except ApiException as err:
        logger.error("Exception : %s\n" % err)

    # Set ImagePull secret for default SA
    imagePullSecretName = "secret-for-pull-image"
    api_instance = kubernetes.client.CoreV1Api()
    sec = kubernetes.client.V1Secret()

    secret_list = api_instance.list_namespaced_secret(name)

    try:
        # Get Original secret
        baseSecret = api_instance.read_namespaced_secret(
            "template-secret-for-pull-image", "kube-system"
        )

        if imagePullSecretName not in [
            item.metadata.name for item in secret_list.items
        ]:
            # Create new secret
            sec.metadata = kubernetes.client.V1ObjectMeta(name=imagePullSecretName)
            sec.type = "kubernetes.io/dockerconfigjson"
            sec.data = baseSecret.data
            api_instance.create_namespaced_secret(namespace=name, body=sec)
            logger.info("Default Image pull secrets created and set on default sa")

        # Patch default serviceaccount
        sa_patch = {"imagePullSecrets": [{"name": imagePullSecretName}]}
        api_instance.patch_namespaced_service_account(
            name="default", namespace=name, body=sa_patch
        )

    except ApiException as err:
        logger.error("Exception : %s\n" % err)

    ### ResourceQuota Part ###
    resQuotaName = "operator-job-quota"
    api_instance = kubernetes.client.CoreV1Api()

    resquota_list = api_instance.list_namespaced_resource_quota(name)

    try:
        if resQuotaName not in [item.metadata.name for item in resquota_list.items]:
            logger.info(f"Jobs Quota must be installed")
            jobquota = os.getenv("QUOTA_JOB", "200")
            rqv1 = kubernetes.client.CoreV1Api()

            resource_quota = kubernetes.client.V1ResourceQuota(
                spec=kubernetes.client.V1ResourceQuotaSpec(
                    hard={"count/jobs.batch": jobquota}
                )
            )
            resource_quota.metadata = kubernetes.client.V1ObjectMeta(
                namespace=name, name="operator-job-quota"
            )
            rqv1.create_namespaced_resource_quota(name, resource_quota)

    except ApiException as err:
        logger.error("Exception : %s\n" % err)

    ### LimitRange Part ###
    lrName = "operator-limit-range"
    api_instance = kubernetes.client.CoreV1Api()

    lr_list = api_instance.list_namespaced_limit_range(name)

    try:
        if lrName not in [item.metadata.name for item in lr_list.items]:
            logger.info(f"Limit Range must be installed")
            cpulimit = os.getenv("LIMIT_CPU", "4")
            memorylimit = os.getenv("LIMIT_MEMORY", "4Gi")
            lrv1 = kubernetes.client.CoreV1Api()

            limit_range = kubernetes.client.V1LimitRange(
                spec=kubernetes.client.V1LimitRangeSpec(
                    limits=[
                        kubernetes.client.V1LimitRangeItem(
                            type="Container",
                            max={"memory": memorylimit, "cpu": cpulimit},
                            default_request={"memory": "64M", "cpu": "50m"},
                        )
                    ]
                )
            )
            limit_range.metadata = kubernetes.client.V1ObjectMeta(
                namespace=name, name="operator-limit-range"
            )
            lrv1.create_namespaced_limit_range(name, limit_range)
    except ApiException as err:
        logger.error("Exception : %s\n" % err)


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    ns_created("kube-system", logging)