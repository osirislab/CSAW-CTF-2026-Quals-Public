Challenge Name: Recon: Two Marks, One Score
Author: Rob Gilligan
Category: OSINT
Difficulty: Medium

Challenge Summary:
Two images of filming locations of The Italian Job (2003) are provided (Campo San Barnaba, Venice & Hollywood/Highland Metro station, LA). Players must use each image to identify the specific location, then cross reference film location data to find the movie production that used both. Flag is the helicopter id number seen in the final scenes

Player Goal: 
Identify the filming location shown in each of two provided images, then determine the single film that used both locations during production. 

Intended Solve Path: 
1. Player receives two images & flavor text. The Author name is also a small convoluted hint
2. Image 1 (rooftop view near Campo San Barnaba, Venice): reverse image search to identify specific landmark.
3. Image 2 (Metro logo + building with palm tree, Hollywood & Highland): reverse image search identifies this as a LA Metro station, player looks at LA Metro's system map/station list to identify potential options and uses google maps to walk around each to find palm trees in line of sight from station
4. Player searches a filming location databases or just asks AI what movie has been filmed in these locations (answer will come up easily from giving it both locations unfortunately)
5. Finds the Italian Job
6. Player watches final heist scene to get tail number of the helicopter
7. Submit: csaw{N723KP}

Alternative solve path: 
1. Look at all author names on associated challenges
2. Google them
3. Continues with step 5 above

Hosting: 
Upload two image files to CTFd for players to download/view & flavor text on CTFd

Flavor text to include as challenge description: 
Every operation starts the same way. Eyes on the ground, long before the crew ever shows up.

Our analysts pulled two photos from a set of surveillance archives. The first looks like the corner of some fancy building, the other of what seems like a company logo with no obvious connection between them.

Except there is one, both coordinates were found in the target's travel manifest. Find out what operation they were casing. The answer is the identifier high in the sky on the day of the operation. We've tracked it to a potential man on the inside. 

Once you know what we're dealing with, keep watching. This crew doesn't stop at scouting, they might have someone on the inside already. We've started tracking their potential entry point. Head to Breach: Zero Day when you're ready to follow their trail.

Flag format: csaw{ANSWERHERE} 

Flag: 
csaw{N723KP}