# Introduction
This software is an SMS Gateway Consolidator.This works on a laptop that is connected to various older mobile devices on the same local Wi-Fi network. 

# Concept
The idea is that the older mobiles can act as SMS_Recievers and the Laptop connected to these mobiles can aggregate all the SMSes recieved in a PostgreSQL database on the laptop.
Repeat SMSes sent are filtered and only unique SMS numbers are forwarded to the Cloud Database. This example uses D1 on Cloudflare.
This method can be used to verify mobile numbers that have been written to D1 already via an IP input. 
Users can send SMS to the older mobile numbers to confirm their mobile numbers after having submitted an onboarding application via IP/Ethernet network.

# Planned Updates
Multiple older mobile devices connected.

# Setup required on Laptop
The following softwares will need to be manually installed on the laptop prior to running this software.
- Docker
- Docker-Compose
- Ansible

# Setup required on older mobile(s)
- SMS_Gateway
Note: Might need rooted mobile or mobile to be on developer mode for this package to be installed.

# How to run
1) Create Ansible vault secret for Postgres, Redis, Grafana and Ansible vault. This will setup ansible vault.yml. The example file for this is TBA.
2) Run the ansible script setup_sms_gateway.yml. Use this command on bash in Linux/WSL: ansible-playbook -i localhost, setup_sms_gateway.yml --ask-vault-pass --ask-become-pass --connection=local -vvv
3) This will pull the necessary containers and the necessary connections to them.
4) Once script completes check that the containers have started using :docker ps
5) Start 
