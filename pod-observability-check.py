import os
import logging
import json
import requests
from kubernetes import client, config
from kubernetes.client.rest import ApiException
import sys
from datetime import datetime, timezone

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

DYNATRACE_API_URL = os.getenv("DYNATRACE_API_URL")
DYNATRACE_API_TOKEN = os.getenv("DYNATRACE_API_TOKEN")
NAMESPACES = os.getenv("POD_NAMESPACES", "default").split(",")  # List of namespaces

try:
    LABELS_TO_CHECK = json.loads(os.getenv("LABELS_TO_CHECK", '[{"label_key": "observable", "label_value": "false"}]'))
except json.JSONDecodeError as e:
    logger.error(f"Failed to parse LABELS_TO_CHECK: {e}")
    sys.exit(1)

if not DYNATRACE_API_URL or not DYNATRACE_API_TOKEN:
    logger.error("DYNATRACE_API_URL or DYNATRACE_API_TOKEN environment variable is not set.")
    sys.exit(1)

def send_alert_to_dynatrace(pod_details):
    """Sends an alert to Dynatrace."""
    try:
        payload = {
            "eventType": "CUSTOM_ALERT",
            "title": f"Pod {pod_details['POD Name']} in namespace {pod_details['Namespace']} is not observable",
            "description": f"The pod {pod_details['POD Name']} has the label 'observable=false'.",
            "entitySelector": f"type(POD),entityId({pod_details['POD Name']})",
            "properties": pod_details,
            "startTime": f"Started: {pod_details['Start Time']}"
        }
        headers = {
            "Authorization": f"Api-Token {DYNATRACE_API_TOKEN}",
            "Content-Type": "application/json"
        }
        response = requests.post(f"{DYNATRACE_API_URL}/api/v2/events/ingest", headers=headers, json=payload)
        response.raise_for_status()
        logger.info(f"Alert sent successfully for pod {pod_details['POD Name']}.")
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to send alert for pod {pod_details['POD Name']}: {e}")

def get_pod_details(pod):
    """Extracts required details from a pod object."""
    return {
        "POD Name": pod.metadata.name,
        "Namespace": pod.metadata.namespace,
        "Node": pod.spec.node_name,
        "IP": pod.status.pod_ip,
        "Status": pod.status.phase,
        "Start Time": pod.status.start_time.isoformat() if pod.status.start_time else "Unknown",
        "Image": ", ".join([container.image for container in pod.spec.containers]),
    }

def get_pods_with_labels(namespace):
    """Fetches all pods in a namespace and checks for the configured labels."""
    try:
        config.load_incluster_config()
        v1 = client.CoreV1Api()
        pods = v1.list_namespaced_pod(namespace=namespace)
        
        matching_pods = []
        for pod in pods.items:
            for label in LABELS_TO_CHECK:
                if label["label_key"] in pod.metadata.labels and pod.metadata.labels[label["label_key"]] == label["label_value"]:
                    pod_details = get_pod_details(pod)
                    matching_pods.append(pod_details)

        return matching_pods

    except ApiException as e:
        logger.error(f"Exception when calling Kubernetes API for namespace '{namespace}': {e}")
        return []

def main():
    all_matching_pods = []
    for namespace in NAMESPACES:
        logger.info(f"Checking pods in namespace: {namespace}")
        matching_pods = get_pods_with_labels(namespace)
        all_matching_pods.extend(matching_pods)

    if all_matching_pods:
        for pod_details in all_matching_pods:
            logger.info(f"Pod {pod_details['POD Name']} with label found.")
            send_alert_to_dynatrace(pod_details)
    else:
        logger.info("No pods with matching labels found.")

if __name__ == "__main__":
    main()