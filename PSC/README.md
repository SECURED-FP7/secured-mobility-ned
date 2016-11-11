# Description of the Mobility API
=================================

The API code can be found [here](manager/mobReport.py). The main purpose of this API is to receive the signal strenghts of the wifi access points near the client and evaluate them to decide if the migration is needed. The algorithm to determine if it is necessary to migrate consists in the comparison of the weighted average of the last four signal strenghts of each wifi access point.
  
The JSON format received from the client is:
```
{
"currentConnection": 
  {
    "ssid": "secured4", 
    "bssid": "00:13:F7:12:13:C8"
  }, 
  "ap-list": 
  [
  {
    "signal": 100.0, 
    "ssid": "secured3", 
    "bssid": "60:E3:27:0F:91:9D"
  }, 
  {
    "signal": 91.42857142857143, 
    "ssid": "secured4", 
    "bssid": "00:13:F7:12:13:C8"
  }
], 
  "user": "test2", 
  "allowHandover": "yes"
}
```

And the responses that the PSC can answer are the following:

If there is no need to start the migration:
```
{
  "action": 0
}
```
If the migration is needed, the PSC requests the TVDM to start the migration and responds to the client that the migration is in progress:
```
{
  "action": 1
}
```
Once the migration is almost finished and it is time for the client to change the wifi connection (Handover):
```
{
  "action": 2, 
  "bssid": "60:E3:27:0F:91:9D",
  "ssid:"secured3"
}
```





