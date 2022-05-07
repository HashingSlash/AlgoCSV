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

def importAlgoRolo():
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
            print('Downloading addressDB and appDB from github (AlgoRolo)')
            r = requests.get('https://raw.githubusercontent.com/HashingSlash/AlgoRolo/main/AlgoAddressDB.json')            
            addressDB = r.json()
            r = requests.get('https://raw.githubusercontent.com/HashingSlash/AlgoRolo/main/AlgoAppDB.json')
            appDB = r.json()
            saveDB(addressDB, 'resources/addressDB')
            saveDB(appDB, 'resources/appDB')
            print('Success')
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

#------------# Partner Checking
def partnerIDCheck(txnRaw, addressDB, appDB):
    txnDetails = txnTypeDetails(txnRaw)
    if txnRaw['sender'] in addressDB:
        result = addressDB[txnRaw['sender']]
    elif 'receiver' in txnDetails and txnDetails['receiver'] in addressDB:
        result = addressDB[txnDetails['receiver']]    
    elif txnRaw['tx-type'] == 'appl' and str(txnDetails['application-id']) in appDB:
            result = appDB[str(txnDetails['application-id'])]
    else: result = ''
    return result

#------------# Group Checking
#def groupIDCheck(txnRaw, groupDB, wallet):
def groupIDCheck(txnRaw, wallet, addressDB, appDB):
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

        

            
        if 'foreign-apps' in txnDetails and len(txnDetails['foreign-apps']) > 0:
            foreignApps = txnDetails['foreign-apps']
            if str(foreignApps[0]) in appDB:
                result = appDB[str(foreignApps[0])]

        if str(txnDetails['application-id']) in appDB:
            result = appDB[str(txnDetails['application-id'])]
        
        if 'application-args' in txnDetails:
            
            appArg = txnDetails['application-args']
            if appArg != []:
                if 'Tinyman' in result:
                    if appArg[0] == 'Ym9vdHN0cmFw':
                        if len(result) == 2: result.append('Bootstrap Pool')
                    elif appArg[0] == 'c3dhcA==':
                        if appArg[1] == 'Zmk=':
                            if len(result) == 2: result.append('Trade: Sell')
                        elif appArg[1] ==  'Zm8=':
                            if len(result) == 2: result.append('Trade: Buy')
                    elif appArg[0] == 'bWludA==':
                        if len(result) == 2: result.append('LP Mint')
                    elif appArg[0] == 'YnVybg==':
                        if len(result) == 2: result.append('LP Burn')
                    elif appArg[0] == 'cmVkZWVt':
                        if len(result) == 2: result.append('Redeem slippage')
                if 'Yieldly' in result:
                    if appArg[0] == 'RA==':
                        if len(result) == 2: result.append('Stake: ALGO - NLL')
                    elif appArg[0] == 'Uw==':
                        if len(result) == 2: result.append('Stake: t3')
                    elif appArg[0] == 'Vw==':
                        if len(result) == 2: result.append('Unstake: t3')
                    elif appArg[0] == 'Q0E=':
                        if len(result) == 2: result.append('Claim: t3')
                    elif appArg[0] == 'Y2xvY2tfb3V0':
                        if len(result) == 2: result.append('Opt Out: t3')
                    elif appArg[0] == 'c3Rha2U=':
                        if len(result) == 2: result.append('Stake: t5')
                    elif appArg[0] == 'Y2xhaW0=':
                        if len(result) == 2: result.append('Claim: t5')
                    elif appArg[0] == 'YmFpbA==':
                        if len(result) == 2: result.append('Withdraw: t5')
                    
                if appArg[0] == 'U1dBUA==': result = ['Pact', 'Swap']
                elif appArg[0] == 'QURETElR': result = ['Pact', 'LP Mint']
                elif appArg[0] == 'UkVNTElR': result = ['Pact', 'LP Unmint']
                elif appArg[0] == 'ZXhlY3V0ZQ==': result = ['Algodex']
                elif appArg[0] == 'ZXhlY3V0ZV93aXRoX2Nsb3Nlb3V0': result = ['Algodex']



                elif appArg[0] == 'YmEybw==': result = ['AlgoFi', 'LP Burn']
                elif appArg[0] == 'cnBhMXI=': result = ['AlgoFi', 'LP Mint']

    return result

def txnAsRow(txnRaw, wallet, walletName, groupDB, addressDB, appDB):
    txnDetails = txnTypeDetails(txnRaw)
    ###SINGLE TXN PROCESSING
    row = []
    #Type
    row.append(txnRaw['tx-type'])
    #Buy/In Amount
    if 'amount' in txnDetails and txnDetails['receiver'] == wallet:
        row.append(txnDetails['amount'])
    else:
        row.append('BA')
    #Buy/In Cur.
    if 'receiver' in txnDetails and txnDetails['receiver'] == wallet:
        if txnRaw['tx-type'] == 'pay':
            row.append('ALGO')
        elif txnRaw['tx-type'] == 'axfer' and 'asset-id' in txnDetails:
            row.append(txnDetails['asset-id'])
    else:
        row.append('BC')
    #Sell/Out Amount
    if 'amount' in txnDetails and txnRaw['sender'] == wallet:
        row.append(txnDetails['amount'])
    else:
        row.append('SA')
    #Sell/Out Cur.
    if txnRaw['sender'] == wallet:
        if txnRaw['tx-type'] == 'pay':
            row.append('ALGO')
        elif txnRaw['tx-type'] == 'axfer' and 'asset-id' in txnDetails:
            row.append(txnDetails['asset-id'])
        else: row.append('SC')
    else:
        row.append('SC')
    #Fee Amount
    if txnRaw['fee'] > 0:
        row.append(txnRaw['fee'])
    else:
        row.append('FA')
    #Fee Cur.
    if txnRaw['fee'] > 0:
        row.append('ALGO')
    else:
        row.append('FC')
    #Exchange/Wallet ID
    row.append(walletName)
    #Trade Group/Platform 
    row.append(groupIDCheck(txnRaw, wallet, addressDB, appDB))
    #Comment/txnID/groupID
    if 'group' in txnRaw:
        row.append(txnRaw['group'])
    else:
        row.append(txnRaw['id'])
    #Date
    date = str(datetime.datetime.fromtimestamp(txnRaw['round-time']))
    row.append(date)

    return row
    
