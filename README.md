# Prisma SD-WAN Get Branch Global Networks (Preview)
The purpose of this script is to get all interface, static and BGP global branch prefixes then export to CSV

#### License
MIT

#### Requirements
* Active Prisma SD-WAN tenant
* Python >=3.7

#### Installation:
 Scripts directory. 
 - **Github:** Download files to a local directory, manually run the scripts. 
 - pip install -r requirements.txt
 
### Examples of usage:
 Please generate your TSG ID, Client ID and Client Secret then add them to prisma_settings.py file
 Please update the remote_networks.csv with all the Remote Networks you want to build 
 
 - ./get_all_branch_routes.py
 
 This script does not commit the changes. That must be done from the portal. 
 
### Caveats and known issues:
 - This is a PREVIEW release, hiccups to be expected. Please file issues on Github for any problems.

#### Version
| Version | Build | Changes |
| ------- | ----- | ------- |
| **1.0.0** | **b1** | Initial Release. |


#### For more info
 * Get help and additional Prisma Access Documentation at <https://pan.dev/sase/>
