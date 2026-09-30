Challenge Name: Breach: Zero Day
Author: Stella Crocker
Category: Forensics
Difficulty: Easy

Challenge Summary:
Three artifacts are left behind containing details of the attackers tools. A network capture, exported windows event log, and a memory dump. These are based off of a 2026 CVE on Windows AFD.sys. Players must locate the correct details within each file to submit as the flag. It is a combination of the C2 indicator, a disabled defense, and the backdoor. 

Player Goal: 
Identify the correct artifacts the attackers left behind and submit all 3 as one correct flag. 

Intended Solve Path: 
1. Open fenwick_capture.pcap. Most of the capture is TLS noise. Filtering to http shows two plaintext POST /api/sync requests
2. Attempt to decode both. backup-vault.fenwick.local's decodes to BACKUPSVC. docs-fenwick-portal.com's is split across two segments, following the full TCP stream reassembles it to RELAYSHELL
3. Both seem workable at this point. Figure out the tie with connection metadata. svc-update-check.net and sync-agent-cdn.com both show connections across the entire capture window. The internal monitoring (10.14.0.9) checks in every 5 minutes all night, then goes silent at 01:09:46 UTC and doesn't come back.
4. docs-fenwick-portal.com begins a pattern at 01:14:25 UTC which is when the monitoring gap opens. That correlation should lead players to submit RELAYSHELL over BACKUPSVC
5. The next question is what security related service changed state around that moment. Searching fenwick_security.xml for antivirus/security service activity near that timestamp turns up "WinDefend" 3 times. Two restart within 30-45 seconds & the third never does and also has a driver event 5 seconds before it. That should indicate the real service. (There's also a unrelated BkupAgent64.sys/SecurityHealthService pair sitting near the BACKUPSVC timestamp, a trap for LLMs looking for easily put together info found in step 3)
6. Search fenwick_memdump.txt for tool names. Two are found: ELUDOMDUF (FUDMODULE) and EGDEHREPPOC (COPPERHEDGE). Both are decoys again, the actual backdoor is harder to find. Two fragments (REGIT, TSEROF) assemble into FORESTTIGER, it's gotta be the hardest one to reassemble right? but LLMs didn't flag this easily as they can find all 3 quickly
7. Submit csaw{RELAYSHELL_WINDEFEND_FORESTTIGER}

Hosting: 
Three files to upload, fenwick_capture.pcap, fenwick_security.xml, and fenwick_memdump.txt. Ignore .gitattributes

Flavor text to include as challenge description: 

--- Incoming Brief - 4:56 AM EST ---
The identification number checked out. It traced back to a private aircraft used for executive travel at Fenwick Analytics. We confirmed what the manifest coordinates suggested, someone had been tracking where Fenwick's leadership went, and when. Whoever this was is casing the company. We don't know why, and we don't know which executive they're targeting. 

This intel leads us to assume they're trying to get into the company, either physically or electronically. We don't know which yet. The second option is easier so let's put our resources there. Fenwick Analytics has offices across multiple different sites, so this crew has many targets. Standby while we work with our analysts. 
--- End Brief ---

--- Incoming Brief - 6:33 AM EST ---
Our analysts put together a brief on Fenwick, suggesting that their Toulouse site might be a likely target. It runs a standard day shift, gates open at 8, and the last people to leave are gone before 7 PM latest. We let them know about the potential attack and are working with them now, pulling network captures, system logs, and memory images from at risk workstations that run overnight operations. Badge logs showed nothing unusal, but we found traces of something unusual moving through the network at odd hours. 

Public data shows that the patterns we are seeing could align with actions of a specific group, but we have not been able to identify which one. These groups are known to borrow from each other's playbooks, so keep an eye out for any anomalies. Once you find these, maybe we can stop them before they exfiltrate anything too serious. 

Three exhibits came out of the investigation:

fenwick_capture.pcap
fenwick_security.xml
fenwick_memdump.txt

See you again in the finals Agent.  
--- End Brief ---

Flag format: csaw{C2INDICATOR_SERVICENAME_BACKDOORNAME}


Flag: 
csaw{RELAYSHELL_WINDEFEND_FORESTTIGER}