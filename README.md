# Blockchain

The baseline code is adopted from https://github.com/adilmoujahid/blockchain-python-tutorial.

There are two python files:-
1. blockchain.py
2. main.py


## 1. blockchain.py
It contains the class implementation for blockchain are the supporting methods in side class. PBFT functions are implemented outside class.

## 2. main.py
This file is executable. It creates blockchain nodes, add transaction and then startking revoking and request process untill it prints complete.


## EXECUTION

main.py requires python version3.7 to execute and before execution all the necessary package updates are require. Anaocanda provides all the packages necessary. Otherwise manually install pycryptodome and other supporting libraries. 

The folder in which it executes must have a folder 'logs' because program generates logs on transactions.

## USAGE
It takes 6 command line arguments. Use the following command and arguments

python3.7 executer.py <no of nodes> <PoV or PoA> <Port Factor> <IoT_1> <IoT_2> <Log suffics>

where

no of nodes : Integer (2, 3, 4 ...)

PoV or PoA  : 0 for mining, 1 for PBFT

Port Factor : Port to run nodes on localhost e.g. 5000. If there are 10 nodes, 5000 will be incremented sequentially

IoT_1 : Number of IoT devices in network 1

IoT_2 : Number of IoT devices in network 2

Log suffics : string (suffix to add at the endof self generating log files)




