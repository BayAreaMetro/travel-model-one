# createLocalBusKNRs.awk
#
# the purpose of this script is to 
# create walk and drive egress links from TP+ created drive access links, 
# by reversing the nodes and increasing the mode
# number by 5.
#
# usage: gawk -f createLocalBusKNRs.awk [transit walk access support link filename] > [bus KNR access support link filename]

{
gsub("="," = ",$0)
gsub("-"," - ",$0)
    
if (($9 == 1) || ($9 == 6)){
    $9 = $9 + 1
    
    if ($12 != 0){
    	$15 = 20.0
    }

    gsub(" = ","=",$0)
    gsub(" - ","-",$0)
    gsub(" , ",",",$0)

    print $0

}

}