from collections import OrderedDict

import binascii
import Crypto
import Crypto.Random
from Crypto.Hash import SHA
from Crypto.PublicKey import RSA
from Crypto.Signature import PKCS1_v1_5

import hashlib
import json
from time import time
try:
    from urllib.parse import urlparse
except ImportError:
    from urlparse import urlparse
    
# from urllib.parse import urlparse
from uuid import uuid4

import requests
from flask import Flask, jsonify, request, render_template
from flask_cors import CORS



MINING_SENDER = "THE BLOCKCHAIN"
MINING_REWARD = 1
MINING_DIFFICULTY = 2


class Blockchain:

    node_add = {}
    num = 0

    def __init__(self):
        
        self.transactions = []
        self.chain = []
        self.nodes = set()
        #Generate random number to be used as node_id
        self.node_id = str(uuid4()).replace('-', '')
        #Create genesis block
        self.create_block(0, '00')


    def register_node(self, node_url):
        """
        Add a new node to the list of nodes
        """
        #Checking node_url has valid format
        parsed_url = urlparse(node_url)
        if parsed_url.netloc:
            self.nodes.add(parsed_url.netloc)
        elif parsed_url.path:
            # Accepts an URL without scheme like '192.168.0.5:5000'.
            self.nodes.add(parsed_url.path)
        else:
            raise ValueError('Invalid URL')


    def verify_transaction_signature(self, sender_address, signature, transaction):
        """
        Check that the provided signature corresponds to transaction
        signed by the public key (sender_address)
        """
        public_key = RSA.importKey(binascii.unhexlify(sender_address))
        verifier = PKCS1_v1_5.new(public_key)
        h = SHA.new(str(transaction).encode('utf8'))
        return verifier.verify(h, binascii.unhexlify(signature))


    def submit_transaction(self, sender_address, recipient_address, value, signature):
        """
        Add a transaction to transactions array if the signature verified
        """
        transaction = OrderedDict({'sender_address': sender_address, 
                                    'recipient_address': recipient_address,
                                    'value': value})

        
        self.transactions.append(transaction)
        return len(self.chain) + 1
    

        # #Reward for mining a block
        # if sender_address == MINING_SENDER:
        #     self.transactions.append(transaction)
        #     return len(self.chain) + 1
        # #Manages transactions from wallet to another wallet
        # else:
        #     transaction_verification = self.verify_transaction_signature(sender_address, signature, transaction)
        #     if transaction_verification:
        #         self.transactions.append(transaction)
        #         return len(self.chain) + 1
        #     else:
        #         return False


    def create_block(self, nonce, previous_hash):
        """
        Add a block of transactions to the blockchain
        """
        block = {'block_number': len(self.chain) + 1,
                'timestamp': time(),
                'transactions': self.transactions,
                'nonce': nonce,
                'previous_hash': previous_hash}

        # Reset the current list of transactions
        self.transactions = []

        self.chain.append(block)
        return block


    def hash(self, block):
        """
        Create a SHA-256 hash of a block
        """
        # We must make sure that the Dictionary is Ordered, or we'll have inconsistent hashes
        block_string = json.dumps(block, sort_keys=True).encode()
        
        return hashlib.sha256(block_string).hexdigest()


    def proof_of_work(self):
        """
        Proof of work algorithm
        """
        last_block = self.chain[-1]
        last_hash = self.hash(last_block)

        nonce = 0
        while self.valid_proof(self.transactions, last_hash, nonce) is False:
            nonce += 1

        return nonce


    def valid_proof(self, transactions, last_hash, nonce, difficulty=MINING_DIFFICULTY):
        """
        Check if a hash value satisfies the mining conditions. This function is used within the proof_of_work function.
        """
        guess = (str(transactions)+str(last_hash)+str(nonce)).encode()
        guess_hash = hashlib.sha256(guess).hexdigest()
        return guess_hash[:difficulty] == '0'*difficulty


    def valid_chain(self, chain):
        """
        check if a bockchain is valid
        """
        last_block = chain[0]
        current_index = 1

        while current_index < len(chain):
            block = chain[current_index]
            #print(last_block)
            #print(block)
            #print("\n-----------\n")
            # Check that the hash of the block is correct
            if block['previous_hash'] != self.hash(last_block):
                return False

            # Check that the Proof of Work is correct
            #Delete the reward transaction
            transactions = block['transactions'][:-1]
            # Need to make sure that the dictionary is ordered. Otherwise we'll get a different hash
            transaction_elements = ['sender_address', 'recipient_address', 'value']
            transactions = [OrderedDict((k, transaction[k]) for k in transaction_elements) for transaction in transactions]

            if not self.valid_proof(transactions, block['previous_hash'], block['nonce'], MINING_DIFFICULTY):
                return False

            last_block = block
            current_index += 1

        return True

    def resolve_conflicts(self):
        """
        Resolve conflicts between blockchain's nodes
        by replacing our chain with the longest one in the network.
        """
        neighbours = self.nodes
        new_chain = None

        # We're only looking for chains longer than ours
        max_length = len(self.chain)

        # Grab and verify the chains from all the nodes in our network
        for node in neighbours:
            print('http://' + node + '/chain')
            response = requests.get('http://' + node + '/chain')

            if response.status_code == 200:
                length = response.json()['length']
                chain = response.json()['chain']

                # Check if the length is longer and the chain is valid
                if length > max_length and self.valid_chain(chain):
                    max_length = length
                    new_chain = chain

        # Replace our chain if we discovered a new, valid chain longer than ours
        if new_chain:
            self.chain = new_chain
            return True

        return False


class Transaction:

    def __init__(self, sender_address, sender_private_key, recipient_address, value):
        self.sender_address = sender_address
        self.sender_private_key = sender_private_key
        self.recipient_address = recipient_address
        self.value = value

    def __getattr__(self, attr):
        return self.data[attr]

    def to_dict(self):
        return OrderedDict({'sender_address': self.sender_address,
                            'recipient_address': self.recipient_address,
                            'value': self.value})

    def sign_transaction(self):
        """
        Sign transaction with private key
        """
        private_key = RSA.importKey(binascii.unhexlify(self.sender_private_key))
        signer = PKCS1_v1_5.new(private_key)
        h = SHA.new(str(self.to_dict()).encode('utf8'))
        return binascii.hexlify(signer.sign(h)).decode('ascii')



def new_wallet():
    random_gen = Crypto.Random.new().read
    private_key = RSA.generate(1024, random_gen)
    public_key = private_key.publickey()
    response = {
        'private_key': binascii.hexlify(private_key.exportKey(format='DER')).decode('ascii'),
        'public_key': binascii.hexlify(public_key.exportKey(format='DER')).decode('ascii')
    }

    return response


def generate_transaction(sender_address, sender_private_key, recipient_address, value):
    
    transaction = Transaction(sender_address, sender_private_key, recipient_address, value)
    response = {'transaction': transaction.to_dict(), 'signature': transaction.sign_transaction()}
    return response



# def new_transaction(blockchain, sender_address, recipient_address, value, signature):
def new_transaction(blockchain, trans):
    # values = request.form # provide these values

    # # Check that the required fields are in the POST'ed data
    # required = ['sender_address', 'recipient_address', 'amount', 'signature']
    # if not all(k in values for k in required):
    #     return 'Missing values', 400
    # Create a new Transaction

    # transaction_result = blockchain.submit_transaction(sender_address, recipient_address, value, signature)

    # ret_sender_add    = gen_trans['transaction']['sender_address']
    # ret_recepient_add = gen_trans['transaction']['recipient_address']
    # ret_value         = gen_trans['transaction']['value']
    # ret_sig           = gen_trans['signature']

    transaction_result = blockchain.submit_transaction(trans['transaction']['sender_address'], trans['transaction']['recipient_address'], trans['transaction']['value'], trans['signature'])

    if transaction_result == False:
        response = {'Invalid Transaction'}
        return 406, response
    else:
        response = {'Transaction added,'+ str(transaction_result)}
        return 201, response


def get_transactions(blockchain):
    #Get transactions from transactions pool
    transactions = blockchain.transactions
    response = {'transactions': transactions}
    return 200, response


def full_chain(blockchain):
    response = {
        'chain': blockchain.chain,
        'length': len(blockchain.chain),
    }
    return 200, response


# Changes required here for 
def mine(blockchain):
    # We run the proof of work algorithm to get the next proof...
    last_block = blockchain.chain[-1]
    nonce = blockchain.proof_of_work()

    # We must receive a reward for finding the proof.
    # blockchain.submit_transaction(sender_address=MINING_SENDER, recipient_address=blockchain.node_id, value=MINING_REWARD, signature="")

    # Forge the new Block by adding it to the chain
    previous_hash = blockchain.hash(last_block)
    block = blockchain.create_block(nonce, previous_hash)

    response = {
        'message': "New Block Forged",
        'block_number': block['block_number'],
        'transactions': block['transactions'],
        'nonce': block['nonce'],
        'previous_hash': block['previous_hash'],
    }
    return 200, response


# Changes required here for 
def mint(blockchain, total_nodes, pid, sock, PORTFACTOR):
    # We run the proof of work algorithm to get the next proof...
    last_block = blockchain.chain[-1]
    nonce = 00

    previous_hash = blockchain.hash(last_block)
    block = blockchain.create_block(nonce, previous_hash)

    response = {
        'message': "New Block Forged",
        'block_number': block['block_number'],
        'transactions': block['transactions'],
        'nonce': block['nonce'],
        'previous_hash': block['previous_hash'],
    }
    # return 200, response
    pbft_preprepare(block, total_nodes, pid, sock, PORTFACTOR)
    return block


def pbft_preprepare(block, total_nodes,pid, sock, PORTFACTOR):
    # t = time()
    x = json.dumps(block)
    message = 'PP>'+str(pid)+'>'+str(time())+'>'+x
    for i in range(0, total_nodes):
        server_address = ('localhost', PORTFACTOR+i)
        if i != pid:
            
            try:
                # print ('sending trans to "%s"' % str(server_address))
                sent = sock.sendto(message.encode(), server_address)
            except Exception as EE:
                print ("Exeception pbft_prepare: ", EE)
    # print ("pbft_preprepare Time: ", time() - t)


def pbft_prepare(sock, total_nodes, pid, message, PORTFACTOR):
    # t = time()
    for i in range(0, total_nodes):
        server_address = ('localhost', PORTFACTOR+i)
        if i != pid:            
            try:
                # print ('sending trans to "%s"' % str(server_address))
                sent = sock.sendto(message.encode(), server_address)
            except Exception as EE:
                print ("Exeception pbft_prepare: ", EE)
    # print ("pbft_prepare Time: ", time() - t)



def pbft_commit(sock, total_nodes, pid, message, PORTFACTOR):
    # t = time()
    for i in range(0, total_nodes):
        server_address = ('localhost', PORTFACTOR+i)
        if i != pid:            
            try:
                # print ('sending trans to "%s"' % str(server_address))
                sent = sock.sendto(message.encode(), server_address)
            except Exception as EE:
                print ("Exeception pbft_commit: ", EE)
    # print ("pbft_commit Time: ", time() - t)



def register_nodes(blockchain):
    values = request.form
    nodes = values.get('nodes').replace(" ", "").split(',')

    if nodes is None:
        return 400, "Error:Please supply a valid list of nodes"

    for node in nodes:
        blockchain.register_node(node)

    response = {
        'message': 'New nodes have been added',
        'total_nodes': [node for node in blockchain.nodes],
    }
    return 201, response



def consensus(blockchain):
    replaced = blockchain.resolve_conflicts()

    if replaced:
        response = {
            'message': 'Our chain was replaced',
            'new_chain': blockchain.chain
        }
    else:
        response = {
            'message': 'Our chain is authoritative',
            'chain': blockchain.chain
        }
    return 200, response


def get_nodes(blockchain):
    nodes = list(blockchain.nodes)
    response = {'nodes': nodes}
    return response






