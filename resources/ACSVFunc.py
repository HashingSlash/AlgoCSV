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

#------------# wallet ID shortener
def walletName(wallet):
    walletNameCut = wallet.zfill(4)
    walletName = walletNameCut[:4] + '...' + walletNameCut[-4:]
    return walletName

#------------# TXN Check
def asaIDCheck(txnRaw, asaDB, asaFetchList):
    if txnRaw['tx-type'] == 'axfer':
        txnDetails = txnRaw['asset-transfer-transaction']
        #if it is not already in the asaDB
        if str(txnDetails['asset-id']) not in asaDB and str(txnDetails['asset-id']) not in asaFetchList:
            #add to asset list. Fetch all missing assets after raw txns
            return txnDetails['asset-id']
        else:
            return ''
    else:
        return ''

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

#------------# 
def asaRequest(asaID):
    #get asa response
    asaResponse = requests.get('https://algoindexer.algoexplorerapi.io/v2/assets/' + str(asaID))
    asaJSON = asaResponse.json()
    #set required details to vars
    if 'asset' not in asaJSON:
        asaName = asaID
        asaTick = asaID
        asaDecimals = 0
    else:
        asaDetails = asaJSON['asset']
        asaParams = asaDetails['params']
        asaDecimals = asaParams['decimals']
        if 'unit-name' in asaParams:
            asaTick = asaParams['unit-name']
        else:
            asaTick = asaID
        if 'name' in asaParams: asaName = asaParams['name']
        else: asaName = asaID
    #build asa dictionary entry
    details = {"id"         : asaID,
               "name"       : asaName,
               "ticker"     : asaTick,
               "decimals"   : asaDecimals}
    #return asa dictionary entry
    return details    

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
##--------##        Row building
def txnAsRow(txnRaw, wallet, walletName, groupDB, addressDB, appDB, asaDB):
    txnDetails = txnTypeDetails(txnRaw)
    ###SINGLE TXN ROW
    
    #Type
    txnType = txnRaw['tx-type']
    
    #Buy/In Amount
    if 'amount' in txnDetails and txnDetails['receiver'] == wallet:
        buyAmount = txnDetails['amount']
    else:
        buyAmount = ''
        
    #Buy/In Cur.
    if 'receiver' in txnDetails and txnDetails['receiver'] == wallet:
        if txnRaw['tx-type'] == 'pay':
            buyCur = 'ALGO'
        elif txnRaw['tx-type'] == 'axfer' and 'asset-id' in txnDetails:
            buyCur = str(txnDetails['asset-id'])
        else: buyCur = ''
    else:
        buyCur = ''
        
    #Sell/Out Amount
    if 'amount' in txnDetails and txnRaw['sender'] == wallet:
        sellAmount = txnDetails['amount']
    else:
        sellAmount = ''
        
    #Sell/Out Cur.
    if txnRaw['sender'] == wallet:
        if txnRaw['tx-type'] == 'pay':
            sellCur = 'ALGO'
        elif txnRaw['tx-type'] == 'axfer' and 'asset-id' in txnDetails:
            sellCur = str(txnDetails['asset-id'])
        else: sellCur = ''
    else:
        sellCur = ''
        
    #Fee Amount
    if txnRaw['fee'] > 0:
        feeAmount = txnRaw['fee']
    else:
        feeAmount = ''
        
    #Fee Cur.
    if txnRaw['fee'] > 0:
        feeCur = 'ALGO'
    else:
        feeCur = ''
        
    #Exchange/Wallet ID
    
    #Trade Group/Platform 
    tradeGroup = groupIDCheck(txnRaw, wallet, addressDB, appDB)
    
    #Comment/txnID/groupID
    if 'group' in txnRaw:
        comment = str('G- ' + txnRaw['group'])
    else:
        comment = str('T- ' + txnRaw['id'])
    
    #Date
    date = str(datetime.datetime.fromtimestamp(txnRaw['round-time']))

    if buyAmount != '':
        buyAmount = decimal(buyCur, asaDB, buyAmount)
    if buyCur in asaDB:
        asaDetails = asaDB[buyCur]
        buyCur = asaDetails['ticker']
    if sellAmount != '':
        seelAmount = decimal(sellCur, asaDB, sellAmount)
    if sellCur in asaDB:
        asaDetails = asaDB[sellCur]
        sellCur = asaDetails['ticker']
    
    row = [txnType, buyAmount, buyCur, sellAmount, sellCur,
           feeAmount, feeCur, walletName, tradeGroup, comment, date]

    return row
    
def rewardsRow(rewards, walletName, txnRaw, asaDB):
    amount = decimal('ALGO', asaDB, rewards)
    return ['Rewards', amount, 'ALGO',
            '', '', '', '',
            walletName, 'Participation Rewards',
            str('R- ' + txnRaw['id'] + ' Rewards'),
            str(datetime.datetime.fromtimestamp(txnRaw['round-time']))]

def innerTxnRow(innerTxn, wallet, walletName, txnRaw, asaDB):
    buyAmount = ''
    buyCur = ''
    sellAmount = ''
    sellCur = ''
    if 'group' in txnRaw:
        txnName = str(txnRaw['group'] + ': inner txn')
    else:
        txnName = str(txnRaw['id'] + ': inner txn')
    if innerTxn['tx-type'] == 'pay':
        innerDetails = innerTxn['payment-transaction']
        innerCur = 'ALGO'
    elif innerTxn['tx-type'] == 'axfer':
        innerDetails = innerTxn['asset-transfer-transaction']
        innerCur = innerDetails['asset-id']
    else:
        return ''
    if innerDetails['receiver'] == wallet:
        buyAmount = innerDetails['amount']
        buyCur = innerCur
    elif innerTxn['sender'] == wallet:
        sellAmount = innerDetails['amount']
        sellCur = innerCur
    if buyAmount != '' or sellAmount != '':
        buyAmount = decimal(buyCur, asaDB, buyAmount)
        sellAmount = decimal(buyCur, asaDB, sellAmount)
        return ['inner txn', buyAmount, buyCur,
                sellAmount, sellCur, '', '',
                walletName, 'inner txn', str(txnName),
                str(datetime.datetime.fromtimestamp(txnRaw['round-time']))]
            

def decimal(asaID, asaDB, baseQ):
    if asaID != 'ALGO':
        asaDetails = asaDB[str(asaID)]
        decimal = asaDetails['decimals']
    else: decimal = 6

    if decimal == 0:
        return baseQ
    else:
        qString = str(baseQ)
        qStringFilled = qString.zfill(decimal)
        return qStringFilled[:-decimal] + '.' + qStringFilled[-decimal:]






