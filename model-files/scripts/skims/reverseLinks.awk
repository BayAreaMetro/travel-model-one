# reverseLinks.awk
#
# the purpose of this script is to 
# create walk and drive egress links from TP+ created drive access links, 
# by reversing the nodes and increasing the mode
# number by 5.
#
# usage: gawk -f reverseLinks.awk [access support link filename] > [egress support link filename]

{
gsub("="," = ",$0)
gsub("-"," - ",$0)

if (($9 == 1) || ($9 == 2) || ($9 == 4)){
    newB = $4
    newA = $6

    $4 = newA
    $6 = newB
    
    if (($9 == 1) || ($9 == 2)){
        $9 = $9 + 5
    }
}

gsub(" = ","=",$0)
gsub(" - ","-",$0)
gsub(" , ",",",$0)

print $0

}