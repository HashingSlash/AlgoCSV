#----------#        IMPORTS
import requests
import json
import csv
import datetime
import base64
import os

def saveDB(DB, name):
    DBJson = json.dumps(DB)
    outFile = open(name + '.json', 'w')
    outFile.write(DBJson)
    outFile.close()

def loadDB(fileName):
    inFile = open(fileName, 'r')
    loadFile = json.load(inFile)
    inFile.close()
    return loadFile

fileDir = os.path.dirname(os.path.realpath('__file__'))

#------------# Known IDs
try:
    addressDB = loadDB('AlgoAddressDB.json')
    appDB = loadDB('AlgoAppDB.json')
    print('Loaded App and Address DBs')
except:
    try:
        addressDB = loadDB('resources/AlgoAddressDB.json')
        appDB = loadDB('resources/AlgoAppDB.json')
        print('Loaded App and Address DBs from resources')
    except:
        addressDB = {}
        appDB = {}
        print('blank App and Address DBs')
    pass

            

#------------# TXN Check
def asaIDCheck(txnRaw, asaDB):
    if txnRaw['tx-type'] == 'axfer':
        txnDetails = txnRaw['asset-transfer-transaction']
        #if it is not already in the asaDB
        if str(txnDetails['asset-id']) not in asaDB:
            #add to asset list. Fetch all missing assets after raw txns
            return txnDetails['asset-id']

def txnTypeDetails(txnRaw):
    if txnRaw['tx-type'] == 'pay':
        return txnRaw['payment-transaction']
    if txnRaw['tx-type'] == 'keyreg':
        pass
    if txnRaw['tx-type'] == 'acfg':
        pass
    if txnRaw['tx-type'] == 'axfer':
        return txnRaw['asset-transfer-transaction']
    if txnRaw['tx-type'] == 'afrz':
        pass
    if txnRaw['tx-type'] == 'appl':
        return txnRaw['application-transaction']

#------------# Group Checking
#def groupIDCheck(txnRaw, groupDB, wallet):
def partnerIDCheck(txnRaw, wallet):
    result = ''

    if txnRaw['sender'] in addressDB: result = addressDB[txnRaw['sender']]
    txnDetails = txnTypeDetails(txnRaw)
    if 'receiver' in txnDetails:
        if txnDetails['receiver'] in addressDB: result = addressDB[txnDetails['receiver']]
    
    
    if 'note' in txnRaw:
        decodedNote = str(base64.b64decode(txnRaw['note']))
        if txnRaw['note'] == "YWIyLmdhbGxlcnk=": result = ['ab2.gallery']
        elif txnRaw['note'] == "TWFuYWdlcjogQ2xhaW0gcmV3YXJkcw==": result = ['AlgoFi', 'Claim Rewards']
        elif wallet in decodedNote: result = ['Algodex']
        elif 'RIO Rewards' in decodedNote: result = ['RIO', 'Rewards']
        #else: print(decodedNote)
                   
        
    if txnRaw['tx-type'] == 'appl':
        #else: print(str(txnDetails['application-id']))
        if 'local-state-delta' in txnRaw:
            txnLsd = txnRaw['local-state-delta'][0]
            if 'delta' in txnLsd:
                txnLsdDelta = txnLsd['delta'][0]
                if txnLsdDelta['key'] == 'dXNh': result = ['AlgoFi', 'Opt in']

        

                
        
        if 'application-args' in txnDetails:
            appArg = txnDetails['application-args']
            if appArg != []:
                if appArg[0] == 'Ym9vdHN0cmFw': result =   ['Tinyman', 'Bootstrap Pool']
                elif appArg[0] == 'c3dhcA==':
                    if appArg[1] == 'Zmk=': result =   ['Tinyman', 'Trade: Sell']
                    elif appArg[1] ==  'Zm8=': result =   ['Tinyman', 'Trade: Buy']
                elif appArg[0] == 'bWludA==': result =   ['Tinyman', 'LP Mint']
                elif appArg[0] == 'YnVybg==': result =   ['Tinyman', 'LP Burn']
                elif appArg[0] == 'cmVkZWVt': result =   ['Tinyman', 'Redeem slippage']

                elif appArg[0] == 'U1dBUA==': result =   ['Pact', 'Swap']
                elif appArg[0] == 'QURETElR': result =   ['Pact', 'LP Mint']
                elif appArg[0] == 'UkVNTElR': result =   ['Pact', 'LP Unmint']
                elif appArg[0] == 'ZXhlY3V0ZQ==': result =   ['Algodex']
                elif appArg[0] == 'ZXhlY3V0ZV93aXRoX2Nsb3Nlb3V0': result =   ['Algodex']

                elif appArg[0] == 'RA==': result =   ['Yieldly', 'Stake: ALGO - NLL']
                elif appArg[0] == 'Uw==': result =   ['Yieldly', 'Stake: t3']
                elif appArg[0] == 'Vw==': result =   ['Yieldly', 'Unstake: t3']
                elif appArg[0] == 'Q0E=': result =   ['Yieldly', 'Claim: t3']
                elif appArg[0] == 'Y2xvY2tfb3V0': result =   ['Yieldly', 'Opt Out: t3']
                elif appArg[0] == 'c3Rha2U=': result =   ['Yieldly', 'Stake: t5']
                elif appArg[0] == 'Y2xhaW0=': result =   ['Yieldly', 'Claim: t5']
                elif appArg[0] == 'YmFpbA==': result =   ['Yieldly', 'Opt Out: t5']

                elif appArg[0] == 'YmEybw==': result =   ['AlgoFi', 'LP Burn']
                elif appArg[0] == 'cnBhMXI=': result =   ['AlgoFi', 'LP Mint']


        if 'foreign-apps' in txnDetails and len(txnDetails['foreign-apps']) > 0:
            foreignApps = txnDetails['foreign-apps']
            if str(foreignApps[0]) in appDB:
                result = appDB[str(foreignApps[0])]

        if str(txnDetails['application-id']) in appDB:
            result = appDB[str(txnDetails['application-id'])]

    return result

