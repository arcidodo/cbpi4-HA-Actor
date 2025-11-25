# Pre-release - please use with caution

# CraftBeerPI4 Actor Plugin that controls actors via Home Assistant
![GitHub issues](https://img.shields.io/github/issues-raw/arcido/cbpi4-HA-Actor)
[![GitHub license](https://img.shields.io/github/license/craftbeerpi/craftbeerpi4)](https://github.com/craftbeerpi/craftbeerpi4/blob/master/LICENSE)
![PyPI](https://img.shields.io/pypi/v/cbpi4-HA-Actor)



Actor Plugin for Craftbeerpi4 https://github.com/craftbeerpi/craftbeerpi4/ to control devices integrated in HomeAssistant (https://www.home-assistant.io). 
The plugin is using the Home Assitant's REST API.
## Motivation
I am using electric kettles (i.e. german "Einkochautomat" simliar to those https://amzn.to/3miTXHw) for my brewing. I only brew occasionally and always assemble my equipment on our terrace. 
In terms of beer quality and diversity, my equipment works fine and for quite some time I used CraftBeerPi3 with some plugins to either control 433Mhz or TP-Link Wifi plugs to control the kettles, pumps and agitators. However, at some point this occasionally failed on me due to changes in the API, deprecated plugins, newer python versions or whatever. 
My Smarthome on the other hand, can handle all these device nicely and is used every day anyway. So it is much easier (for me) to use Home Assistant's API to control all the devices. It is also opens up all Home Assistant compliant device, which have no plugin for CraftBeerPi (like Shelly) - and best for many I do not need to touch any live wires ;-)


# Features
* Control any actors integrated in Home Assitant regardless of it's protocol (WiFi, ZigBee, LAN etc...)
* Simple power simulation with time proportioning.


# Installation
## Activate REST-API in HA
You need to activate the REST-API in your Home Assitant installation.
Normally, this is archieved by adding `"api:"` to your configuration yaml.

See more info here: https://www.home-assistant.io/integrations/api/

## Get authentication token
To authenticate this plugin against HA you need to generate a "Long-lived Access Token". 
You can generate those in your HA users profile.

A tutorial can be found here: https://www.atomicha.com/home-assistant-how-to-generate-long-lived-access-token-part-1/

*Be aware you only see this once in HA and it's quite long (180 Chars), please save it securily.*

## Install plugin
Currently we only support installation directly from the git repository:
```bash
sudo pip3 install https://github.com/arcidodo/cbpi4-HA-Actor/archive/refs/heads/main.zip
```
Direct pip installation via repositories will come in the near future.

## Configuration
Enter the appropiate configuration:
<img width="739" alt="image" src="https://user-images.githubusercontent.com/244549/172670290-a9d6885a-5cb0-46a4-b84e-db54db8f7fc4.png">


# Known problems
None, *yet*. Please report via "issues"!

