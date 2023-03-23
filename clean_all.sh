#!/bin/bash

KUBECTL="kubectl"
EXCLUDE_NAMESPACE_LIST=""
while [ "$1" != "" ]
do
  case $1 in
    -o | --only )           shift
                            NAMESPACE_LIST=$1
                            ;;  
    -e | --exclude )        shift
                            EXCLUDE_NAMESPACE_LIST=$1
                            ;;
    -h | --help )           echo "usage   ./clean_all.sh -o <only namespaces comma separated> -e <excluded namespaces comma separated>"
                            echo "example ./clean_all.sh -o kube-system"
							              echo "example ./clean_all.sh -e default,kube-system"
                            exit
                            ;;
    * )                     echo "usage   ./clean_all.sh -o <only namespaces comma separated> -e <excluded namespaces comma separated>"
                            echo "example ./clean_all.sh -o kube-system"
							              echo "example ./clean_all.sh -e default,kube-system"
                            exit 1
  esac
  shift
done

function actions() {
  echo WORK ON NAMESPACE: $NS
  $KUBECTL delete networkpolicies.networking.k8s.io namespace-operator -n $NS
  $KUBECTL delete limitranges operator-limit-range -n $NS
  $KUBECTL delete resourcequotas operator-job-quota -n $NS
  $KUBECTL delete secret secret-for-pull-image -n $NS
  $KUBECTL annotate namespace $NS namespace-operator/kopf-managed-
  $KUBECTL annotate namespace $NS namespace-operator/last-handled-configuration-
}

if [ -z $NAMESPACE_LIST ]
then 
  COMPLETE_NAMESPACE_LIST=$($KUBECTL get namespaces -ojsonpath='{.items[*].metadata.name}')
  EXCLUDE_NAMESPACE_LIST=$(echo $EXCLUDE_NAMESPACE_LIST | sed 's/,/ /g')
  NAMESPACE_LIST=$(echo $COMPLETE_NAMESPACE_LIST $EXCLUDE_NAMESPACE_LIST | sed 's/ /\n/g' | sort | uniq -u)
else
  NAMESPACE_LIST=$(echo $NAMESPACE_LIST | sed 's/,/ /g')
fi

for NS in $NAMESPACE_LIST
do
  actions
done