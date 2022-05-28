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
            asaDB = ACSVFunc.loadDB('resources/AlgoAsaDB.json')
            print('Loaded App and Address DBs from resources')
        except:
            print('Downloading addressDB and appDB from github (AlgoRolo)')
            r = requests.get('https://raw.githubusercontent.com/HashingSlash/AlgoRolo/main/AlgoAddressDB.json')            
            addressDB = r.json()
            r = requests.get('https://raw.githubusercontent.com/HashingSlash/AlgoRolo/main/AlgoAppDB.json')
            appDB = r.json()
            r = requests.get('https://raw.githubusercontent.com/HashingSlash/AlgoRolo/main/AlgoAsaDB.json')
            asaDB = r.json()
            saveDB(addressDB, 'resources/addressDB')
            saveDB(appDB, 'resources/appDB')
            saveDB(asaDB, 'resources/asaDB')
            print('Success')
        pass

#------------# wallet ID shortener
    #Return a short wallet 'name'. example - ABCD...WXYZ
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
        return txnRaw['keyreg-transaction']
    if txnRaw['tx-type'] == 'acfg':
        return txnRaw['asset-config-transaction']
    if txnRaw['tx-type'] == 'axfer':
        return txnRaw['asset-transfer-transaction']
    if txnRaw['tx-type'] == 'afrz':
        return txnRaw['asset-freeze-transaction']
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
def algodexGroup(decodedNote, wallet):
    tradeDetails = decodedNote[2::]
    tradeDetails = tradeDetails[:-1:]
    result = []
    try:
        tradeDetails = json.loads(tradeDetails)
        result = ['AlgoDex']
        for entry in tradeDetails:
            if '[open]' in entry:
                result = ['AlgoDex', 'Place Order']
            elif '[close]' in entry:
                result = ['AlgoDex', 'Cancel Order']
            elif '[execute' in entry:
                if wallet in entry:
                    result = ['AlgoDex', 'Take Order']
                else:
            
                    tradeDetails = tradeDetails[entry]
                    if tradeDetails['orderCreatorAddr'] == wallet:
                        result = ['AlgoDex', 'Order Sold']
                    #else: print(tradeDetails)
            #else: print(entry)
    except:
        pass

    print(result)
    return result



#def groupIDCheck(txnRaw, groupDB, wallet):
def groupIDCheck(txnRaw, wallet, addressDB, appDB, groupDB):
    result = ''

    if txnRaw['sender'] in addressDB: result = addressDB[txnRaw['sender']]
    txnDetails = txnTypeDetails(txnRaw)
    if 'receiver' in txnDetails:
        if txnDetails['receiver'] in addressDB: result = addressDB[txnDetails['receiver']]
    
    
    if 'note' in txnRaw:
        decodedNote = str(base64.b64decode(txnRaw['note']))
        if txnRaw['note'] == "YWIyLmdhbGxlcnk=": result = ['ab2.gallery']
        elif txnRaw['note'] == "TWFuYWdlcjogQ2xhaW0gcmV3YXJkcw==": result = ['AlgoFi', 'Claim Rewards']

        elif 'RIO Rewards' in decodedNote: result = ['RIO', 'Rewards']
        #else: print(decodedNote)

        #------------------ Check for AlgoDex ------------
        if wallet in decodedNote:
            print(txnRaw['id'])
            result = algodexGroup(decodedNote, wallet)
            if 'application-args' in txnDetails:
                appArg = txnDetails['application-args']
                #if appArg != []:
                #    
                #    #print(txnRaw['id'])
                #    if appArg[0] == 'ZXhlY3V0ZQ==':     #execute
                #        result = algodexGroup(decodedNote, wallet)
                #    elif appArg[0] == 'ZXhlY3V0ZV93aXRoX2Nsb3Nlb3V0':   #execute with closeout
                #        result = algodexGroup(decodedNote, wallet)
                #    elif appArg[0] == 'b3Blbg==':   #open
                #        result = algodexGroup(decodedNote, wallet)
                #    elif appArg[0] == 'Y2xvc2U=':   #close
                #        result = algodexGroup(decodedNote, wallet)
                #    else:
                #        pass    #print(decodedNote)
        #----------------------------------------------
        
    if txnRaw['tx-type'] == 'appl':
        #else: print(str(txnDetails['application-id']))
        if 'local-state-delta' in txnRaw:
            txnLsd = txnRaw['local-state-delta'][0]
            if 'delta' in txnLsd:
                txnLsdDelta = txnLsd['delta'][0]
                if txnLsdDelta['key'] == 'dXNh': result = ['AlgoFi', 'Opt in']

        

            
        if 'foreign-apps' in txnDetails and len(txnDetails['foreign-apps']) > 0:
            foreignApps = txnDetails['foreign-apps']
            for app in foreignApps:
                if app in appDB:
                    result = appDB[app]

        if str(txnDetails['application-id']) in appDB:
            result = appDB[str(txnDetails['application-id'])]
        
        if 'application-args' in txnDetails:
            
            appArg = txnDetails['application-args']
            if appArg != []:
                #------------------------------------
                if 'Tinyman' in result:
                    if appArg[0] == 'Ym9vdHN0cmFw':
                        result = ['Tinyman', 'Bootstrap Pool']
                    elif appArg[0] == 'c3dhcA==':
                        if appArg[1] == 'Zmk=':
                            result = ['Tinyman' , 'Trade: Fixed Input']
                        elif appArg[1] ==  'Zm8=':
                            result = ['Tinyman', 'Trade: Fixed Output']
                    elif appArg[0] == 'bWludA==':
                        result = ['Tinyman', 'LP Mint']
                    elif appArg[0] == 'YnVybg==':
                        result = ['Tinyman', 'LP Burn']
                    elif appArg[0] == 'cmVkZWVt':
                        result = ['Tinyman', 'Redeem slippage']

                #------------------------------------
                #if 'Yieldly' in result:
                #    if appArg[0] == 'RA==':
                #        if len(result) == 2: result.append('Stake: ALGO - NLL')
                #    elif appArg[0] == 'Uw==':
                #        if len(result) == 2: result.append('Stake: t3')
                #    elif appArg[0] == 'Vw==':
                #        if len(result) == 2: result.append('Unstake: t3')
                #    elif appArg[0] == 'Q0E=':
                #        if len(result) == 2: result.append('Claim: t3')
                #    elif appArg[0] == 'Y2xvY2tfb3V0':
                #        if len(result) == 2: result.append('Opt Out: t3')
                #    elif appArg[0] == 'c3Rha2U=':
                #        if len(result) == 2: result.append('Stake: t5')
                #    elif appArg[0] == 'Y2xhaW0=':
                #        if len(result) == 2: result.append('Claim: t5')
                #    elif appArg[0] == 'YmFpbA==':
                #        if len(result) == 2: result.append('Withdraw: t5')
                #-----------------------------------------
                else:
                    if appArg[0] == 'U1dBUA==': result = ['Pact', 'Trade']
                    elif appArg[0] == 'QURETElR': result = ['Pact', 'LP Mint']
                    elif appArg[0] == 'UkVNTElR': result = ['Pact', 'LP Burn']
                    #-------------------------------------------

                #-------------------------------------------
                #AlgoFi
                    elif appArg[0] == 'c2Vm': result = ['AlgoFi', 'Fixed Input']
                    elif appArg[0] == 'c2Zl': result = ['AlgoFi', 'Fixed Output']
                    elif appArg[0] == 'cA==':
                        if txnRaw['group'] in groupDB and groupDB[txnRaw['group']] == ['AlgoFi', 'Fixed Input']:
                            result = ['AlgoFi', 'Zap']
                        else:
                            result = ['AlgoFi', 'LP Mint']
                    elif appArg[0] == 'YmEybw==': result = ['AlgoFi', 'LP Burn']

    return result



##--------##        Row building
def txnAsRow(txnRaw, wallet, walletName, groupDB, addressDB, appDB, asaDB):
    txnDetails = txnTypeDetails(txnRaw)
    #take a txn and put it into a list for the CSV writer
    #divided up into columns. could be streamlined.

    #Set base vars
    
    #Type
    txnType = txnRaw['tx-type']
    
    #Buy/In Amount
    if 'amount' in txnDetails and txnDetails['amount'] > 0 and txnDetails['receiver'] == wallet:
        txnType = 'Deposit'
        buyAmount = txnDetails['amount']
    elif 'close-amount' in txnDetails and txnDetails['close-amount'] > 0 and txnDetails['receiver'] == wallet:
        txnType = 'Deposit'
        buyAmount = txnDetails['close-amount']
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
    if 'amount' in txnDetails and txnDetails['amount'] > 0 and txnRaw['sender'] == wallet:
        txnType = 'Withdrawal'
        sellAmount = txnDetails['amount']
    else:
        sellAmount = ''
        
    #Sell/Out Cur.
    if txnRaw['sender'] == wallet and 'amount' in txnDetails and txnDetails['amount'] > 0:
        if txnRaw['tx-type'] == 'pay':
            sellCur = 'ALGO'
        elif txnRaw['tx-type'] == 'axfer' and 'asset-id' in txnDetails:
            sellCur = str(txnDetails['asset-id'])
        else: sellCur = ''
    else:
        sellCur = ''
        
    #Fee Amount
    if txnRaw['fee'] > 0 and txnRaw['sender'] == wallet:
        feeAmount = decimal(txnRaw['fee'], 'ALGO', asaDB)
    else:
        feeAmount = ''
        
    #Fee Cur.
    if txnRaw['fee'] > 0 and txnRaw['sender'] == wallet:
        feeCur = 'ALGO'
    else:
        feeCur = ''
        
    #Exchange/Wallet ID
    
    #Trade Group/Platform 
    tradeGroup = groupIDCheck(txnRaw, wallet, addressDB, appDB, groupDB)
    
    #Comment/txnID/groupID
    if 'group' in txnRaw:
        comment = str(txnRaw['group'])
    else:
        comment = str(txnRaw['id'])
    
    #Date
    date = str(datetime.datetime.fromtimestamp(txnRaw['round-time']))

    #Work with base vars

    #Set correct tickers and decimal place when possible
    if buyAmount != '':
        buyAmount = decimal(buyAmount, buyCur, asaDB)
    if buyCur in asaDB:
        asaDetails = asaDB[buyCur]
        buyCur = asaDetails['ticker']
    if sellAmount != '':
        sellAmount = decimal(sellAmount, sellCur, asaDB)
    if sellCur in asaDB:
        asaDetails = asaDB[sellCur]
        sellCur = asaDetails['ticker']
        
    #Network Op Fees
    if buyAmount == '' and sellAmount == '':
        txnType = 'Other Expense'
        tradeGroup = 'Network Operation Fees'

    #-------------------DROP DEFS GO HERE FOR NOW. EXPAND LATER--------------------
    if txnType == 'Deposit' and ('AlgoStake' in tradeGroup or 'The Algo Faucet' in tradeGroup):
        txnType = 'Staking'
        tradeGroup = tradeGroup[0]
    if 'Pact' and 'Rewards' in tradeGroup:
        txnType = 'Staking'
        tradeGroup = 'Pact: Rewards'
        

    #assemble row    
    row = [txnType, buyAmount, buyCur, sellAmount, sellCur,
           feeAmount, feeCur, walletName, tradeGroup, comment, date]
    
    #aHR0cHM6Ly9vcGVuLnNwb3RpZnkuY29tL3RyYWNrLzQzQzB6Wm1QVU5NN3VMeW5Gdm4xanc/c2k9MDAyMTZjNDkwZTZmNDIyOA==
    return row
    
def rewardsRow(rewards, walletName, txnRaw, asaDB):
    amount = decimal(rewards, 'ALGO', asaDB)
    #set txn 'nick-name' for user to locate exactly were a participation reward is within a txn group
    if 'group' in txnRaw:
        shorten = str(txnRaw['group'])
        shortGroup = shorten.zfill(6)
        shorten = str(txnRaw['id'])
        shortTxn = shorten.zfill(6)
        txnName = str('R- G-' + shortGroup[:12] + '...   T- ' + shortTxn[:12] + '...')
    else:
        txnName = str('R- T-' + txnRaw['id'])
        
    return ['Staking', amount, 'ALGO',
            '', '', '', '',
            walletName, 'Participation Rewards', txnName,
            str(datetime.datetime.fromtimestamp(txnRaw['round-time']))]

def innerTxnRow(innerTxn, wallet, walletName, txnRaw, asaDB, groupDB):
    #Set blank row vars
    buyAmount = ''
    buyCur = ''
    sellAmount = ''
    sellCur = ''
    txnType = innerTxn['tx-type']

    #Txn 'nickname' for users reference
    if 'group' in txnRaw:
        shorten = str(txnRaw['group'])
        shortGroup = shorten.zfill(6)
        shorten = str(txnRaw['id'])
        shortTxn = shorten.zfill(6)
        txnName = str('I- G-' + shortGroup[:12] + '...   T-' + shortTxn[:12] + '...')
        if txnRaw['group'] in groupDB:
            txnDef = groupDB[txnRaw['group']]
        else:
            txnDef = ''
    else:
        txnName = str('I- T-' + txnRaw['id'])
        txnDef = 'Inner Txn'

    #Set base vars of inner txn    
    if innerTxn['tx-type'] == 'pay':
        innerDetails = innerTxn['payment-transaction']
        innerCur = 'ALGO'
        innerTick = 'ALGO'
    elif innerTxn['tx-type'] == 'axfer':
        innerDetails = innerTxn['asset-transfer-transaction']
        innerCur = str(innerDetails['asset-id'])
        if innerCur in asaDB:
            CurDetails = asaDB[innerCur]
            innerTick = CurDetails['ticker']
        else: innerTick = innerCur
    else:
        return ''
    #use base vars to set row vars
    if innerDetails['receiver'] == wallet:
        txnType = 'Deposit'
        buyAmount = innerDetails['amount']
        buyCur = innerTick
    elif innerTxn['sender'] == wallet:
        txnType = 'Withdrawal'
        sellAmount = innerDetails['amount']
        sellCur = innerTick
    if buyAmount != '':
        buyAmount = decimal(buyAmount, innerCur, asaDB)
    if sellAmount != '':
        sellAmount = decimal(sellAmount, innerCur, asaDB)

    #assemble row and return it back
    if buyAmount != '' or sellAmount != '':
        return [txnType, buyAmount, buyCur,
                sellAmount, sellCur, '', '',
                walletName, txnDef, str(txnName),
                str(datetime.datetime.fromtimestamp(txnRaw['round-time']))]
            
#func to return number correctly 
def decimal(baseQ, asaID, asaDB):
    if asaID != 'ALGO':
        asaDetails = asaDB[str(asaID)]
        #print(asaDetails)
        decimal = asaDetails['decimals']
    else: decimal = 6

    if decimal == 0:
        return baseQ
    else:
        qString = str(baseQ)
        qStringFilled = qString.zfill(decimal)
        return qStringFilled[:-decimal] + '.' + qStringFilled[-decimal:]


#--------------------------------------------------#
    #MULTIROW FUNCS

def multiRowProcessing(multiRow, txnRow, txnRaw, groupDB):
    rowDef = txnRow[8]
    multiRowTxns = multiRow['txns']
    multiRow['groupID'] = str(txnRaw['group'])
    multiRow['date'] = str(txnRow[10])
    #if a rewards row, store in multiRow and return. no further action required.
    if rowDef == 'Participation Rewards':
        multiRow['rewards'] = txnRow
        return multiRow

    #Group description
    if multiRow['groupID'] in groupDB:
        multiRow['groupDef'] = groupDB[multiRow['groupID']]
    else: multiRow['groupDef'] = ''

    
    #strip and process network fees
    if txnRow[5] != '':
        rowFee = float(txnRow[5])
        
        if rowFee > 0:
            if 'Network Operation Fees' in multiRow:
                #Load saved fees
                netOpFees = float(multiRow['Network Operation Fees'])
            else:
                #Start new fee row
                netOpFees = float('0.000')
            netOpFees = netOpFees + rowFee
            multiRow['Network Operation Fees'] = netOpFees
            #Clear Net Op Fees from row
            txnRow[5] = ''
            txnRow[6] = ''

    if txnRow[1] != '' or txnRow[3] != '':
        if txnRow[8] != 'Pact: Rewards': txnRow[8] = multiRow['groupDef']
        multiRowTxns.append(txnRow)
        multiRow['txns'] = multiRowTxns
        
    return multiRow



def RemoveFeeRow(multiRow, rowNumber):
    netOpFees = float(multiRow['Network Operation Fees'])
    txnRows = multiRow['txns']
    feeRow = txnRows[rowNumber]
    multiRow['Network Operation Fees'] = netOpFees + float(feeRow[3])
    txnRows.remove(feeRow)
    multiRow['txns'] = txnRows
    return multiRow


###----------------AMM Functions----------------------###

def swapRow(multiRow, sentRow, receivedRow, swapType, fee, platform):
    #use outgoing txn to build swap row on
    swapRow = sentRow
    swapRow[0] = 'Trade' #txn type
    swapRow[1] = receivedRow[1] #insert received assets
    swapRow[2] = receivedRow[2] #quantity and ID
    if swapType == 'Zap': swapRow[8] = str(platform + ': Zap')
    else: swapRow[8] = str(platform + ': Trade')
    if fee != 0.0:
        ##places trade fees in fee column
        if swapType == 'Fixed Input':
            i = 100.00 - float(fee)
            feeAsset = float(swapRow[1])
            platformFee = float(((feeAsset * 100)/i) - feeAsset)
            swapRow[5] = platformFee
            swapRow[6] = swapRow[2]
        if swapType == 'Fixed Output':
            i = float(1 - (fee / 100))
            feeAsset = float(swapRow[3])
            platformFee = float(feeAsset - (feeAsset * i))
            swapRow[5] = platformFee
            swapRow[6] = swapRow[4]
    multiRow['groupRows'] = [swapRow]
    return multiRow

def lpAdjust(multiRow, action, platform):
    txns = multiRow['txns']
    #currently for burns and mints
    #will combine two assets and one LP token txn into two rows
    #shows as a Trade. Half the LP tokens for one asset, half for the other.
    slippageRow = []
    #row checking
    if platform == 'Tinyman':
        lpRow1 = txns[0]
        lpRow2 = txns[1]
        tokenRow = txns[2]
    if platform == 'Pact' or platform == 'AlgoFi':
        if action == 'Mint':
            lpRow1 = txns[0]
            lpRow2 = txns[1]
            tokenRow = txns[2]
            if len(txns) > 3:
                slippageRow = txns[3]
                slippageRow[8] = str(platform + ': LP Slippage')
        if action == 'Burn':
            tokenRow = txns[0]
            lpRow1 = txns[1]
            if tokenRow[1] == '.000000' and lpRow1[1] == '.000000':
                return multiRow #solves for burn txns with no assets transfering
            lpRow2 = txns[2]
    
    lpRow1[0] = 'Trade'
    lpRow1[8] = str(platform + ': LP ' + action)
    lpRow2[0] = 'Trade'
    lpRow2[8] = str(platform + ': LP ' + action)
    if action == 'Mint':
        lpRow1[1] = (float(tokenRow[1]))/2
        lpRow1[2] = tokenRow[2]
        lpRow2[1] = (float(tokenRow[1]))/2
        lpRow2[2] = tokenRow[2]
    elif action == 'Burn':
        lpRow1[3] = (float(tokenRow[3]))/2
        lpRow1[4] = tokenRow[4]
        lpRow2[3] = (float(tokenRow[3]))/2
        lpRow2[4] = tokenRow[4]

    if slippageRow != []:
        multiRow['groupRows'] = [lpRow1, lpRow2, slippageRow]
    else: multiRow['groupRows'] = [lpRow1, lpRow2]
    return multiRow

def slippage(multiRow, txn, platform, slippageType):
    if 'groupRows' in multiRow: groupRows = multiRow['groupRows']
    else: groupRows = []
    txn[8] = str(platform + ': ' + slippageType + ' Slippage')
    groupRows.append(txn)
    multiRow['groupRows'] = groupRows
    return multiRow

###------------------------------------------------------------------














