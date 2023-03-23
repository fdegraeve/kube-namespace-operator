# Kube-namespace-operator

This operator adds specific resources to the namespace aka ( network policy, secret for pull image, limitrange & resourcequota ) when creating them

## Contribution
All contributing are welcome :)  

## Pull Request Process

- Fork this repository 
- Create one new branch on this repository
- Once your dev is finished create a new PR.
- Once your PR is validated I merge into master.

The validation of the PR is obligatorily carried out by me.

# Installation 

Secret as reference for pull image on private registry (optional)  
`kubectl create secret docker-registry template-secret-for-pull-image --docker-server=<your-registry-server> --docker-username=<your-name> --docker-password=<your-password> --docker-email=<your-email> -n kube-system`

Edit config map for whitelist namespace (optional)
Add label `namespace-operator.io/global-access: "true"` if a namespace need access to all others namespaces, by example an ingress controller or monitoring like prometheus, you can also change the default [network_policy.yaml](https://github.com/ahmetb/kubernetes-network-policy-recipes).  

Edit env variable in deployment manifest with your default value for quota and limit.    

Installation  
`kubectl apply -f manifest.yaml`

# Uninstall
```
kubectl delete -f manifest.yaml
sh clean_all.sh
```

# Development
[information-for-development](./DEVELOPMENT.md)