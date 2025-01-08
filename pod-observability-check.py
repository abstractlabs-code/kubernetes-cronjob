import os
import logging
import json
import requests
from kubernetes import client, config
from kubernetes.client.rest import ApiException
import sys

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

WEBHOOK_URL = os.getenv("WEBHOOK_URL")
if not WEBHOOK_URL:
    logger.error("WEBHOOK_URL environment variable is not set.")
    sys.exit(1)

NAMESPACE = os.getenv("POD_NAMESPACE", "default")
LABELS_TO_CHECK = json.loads(os.getenv("LABELS_TO_CHECK", '[{"label_key": "observable", "label_value": "false"}]'))

def send_alert(payload):
    """Sends the alert to the external webhook."""
    try:
        response = requests.post(WEBHOOK_URL, json=payload)
        response.raise_for_status()
        logger.info("Alert sent successfully.")
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to send alert: {e}")

def get_pods_with_labels():
    """Fetches all pods and checks for the configured labels."""
    try:
        config.load_incluster_config()
        v1 = client.CoreV1Api()
        pods = v1.list_namespaced_pod(namespace=NAMESPACE)
        
        matching_pods = []
        for pod in pods.items:
            for label in LABELS_TO_CHECK:
                if label["label_key"] in pod.metadata.labels and pod.metadata.labels[label["label_key"]] == label["label_value"]:
                    pod_details = {
                        "name": pod.metadata.name,
                        "namespace": pod.metadata.namespace,
                        "start_time": pod.status.start_time.isoformat() if pod.status.start_time else "Unknown"
                    }
                    matching_pods.append(pod_details)

        return matching_pods

    except ApiException as e:
        logger.error(f"Exception when calling Kubernetes API for namespace '{NAMESPACE}': {e}")
        return []

def generate_alert_payload(pod_details):
    """Generates the payload for the webhook."""
    payload = {
        "ImpactedEntities": pod_details["name"],
        "ImpactedEntity": pod_details["name"],
        "ProblemDetailsText": f"Pod {pod_details['name']} in namespace {pod_details['namespace']} has label 'observable=false'.",
        "ProblemTitle": f"Pod {pod_details['name']} is not observable",
        "ProblemImpact": "High",
        "ProblemSeverity": "Critical",
        "State": "Open",
        "Tags": f"namespace:{pod_details['namespace']},label:observable=false"
    }
    return payload

def main():
    matching_pods = get_pods_with_labels()
    if matching_pods:
        for pod in matching_pods:
            logger.info(f"Pod {pod['name']} with label found. Sending alert...")
            payload = generate_alert_payload(pod)
            send_alert(payload)
    else:
        logger.info("No pods with matching labels found.")

if __name__ == "__main__":
    main()
