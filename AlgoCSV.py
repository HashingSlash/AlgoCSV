
#----------#        IMPORTS
import requests
import json
import csv
import datetime
import base64
import resources.ACSVFunc as ACSVFunc
import os

#Show working directory
fileDir = os.path.dirname(os.path.realpath('__file__'))
print('working in: ' + fileDir)

#----------#        Wallet ID
try:    #Try load previously used wallet address, otherwise promp user for address
    inFile = open('resources/wallet.txt', 'r')
    wallet = inFile.read()
    inFile.close()
    print('Loaded Wallet ID')
except IOError: #Wallet load failed. prompt user to imput
    wallet = str(input('Paste wallet ID and press Enter: '))
    walletFile = open('resources/wallet.txt', 'w')
    walletFile.write(wallet.upper())
    walletFile.close()
    print('Wallet ID saved for next time')

#Shorten wallet ID
walletName = ACSVFunc.walletName(wallet)

    
#try load stored transaction and group databases, or make empty ones
try:
    txnDB = ACSVFunc.loadDB('resources/txnDB.json')
    txnOrder = txnDB['txnOrder']
    groupDB = ACSVFunc.loadDB('resources/groupDB.json')    
    addressDB = ACSVFunc.loadDB('resources/addressDB.json')
    appDB = ACSVFunc.loadDB('resources/appDB.json')
    algodexTakenDB = ACSVFunc.loadDB('resources/algodexTakenDB.json')
    prerunTxnCount = len(txnOrder)
    print(str(len(txnOrder)) + ' txns loaded')
    print(str(len(groupDB.keys())) + ' groups loaded')
    freshDB = 'False'
except IOError: #Create empty list and dictionaries for storing info
    print('Fresh txnDB')
    txnOrder = []
    txnDB = {}
    groupDB = {}
    algodexTakenDB = {}
    prerunTxnCount = 0
    ACSVFunc.importAlgoRolo()
    addressDB = ACSVFunc.loadDB('resources/addressDB.json')
    appDB = ACSVFunc.loadDB('resources/appDB.json')
    freshDB = 'True'

try:
    asaDB = ACSVFunc.loadDB('resources/asaDB.json')
except IOError:
    asaDB = {}
        

#-----          RUN
#-----          Pull txn data
#get recent/all wallet transactions and convert from JSON format
print('Checking newest transactions')
newTxnIDs = []
txnResponse = requests.get('https://algoindexer.algoexplorerapi.io/v2/accounts/'
                           + wallet + '/transactions', params={"limit": 10000})
txnJson = txnResponse.json()
txnCurrent = 'false'    #var to flag when up to date with txns.
asaFetchList = []   #list to store new asaIDs for later processing

for getTxn in txnJson['transactions']:  #for each txn returned
    if getTxn['id'] not in txnDB:   #if txn new
        
        newTxnIDs.insert(0, getTxn['id'])    #add to start of Ordered list for new entries. 
        getTxn.update({'wallet' : wallet})  #add wallet ID to this txn instance. 
        txnDB.update({getTxn['id']: getTxn})    #add this txn instance to txnDB
        asaCheck = str(ACSVFunc.asaIDCheck(getTxn, asaDB, asaFetchList))
        if asaCheck != '': asaFetchList.append(asaCheck)    #if this is the first time seeing this ASA, log to fetch its details.
    elif getTxn['id'] in txnDB:   #If the txn is already in the txnDB, stop processing new txns.
        txnCurrent = 'true'
        continue

#Not all txns will be in the initial get request. if there are more txns, there will be a next-token.
#If you are already up to date, this section is not ran due to txnCurrent var tracking this.
#This section keeps running until no more new txns are returned.
#Script is mostly the same as the first time. May move to function at some point.
while 'next-token' in txnJson and txnCurrent == 'false':
    print('getting more txns: ' + txnJson['next-token'])
    txnResponse = requests.get('https://algoindexer.algoexplorerapi.io/v2/accounts/'
                                + wallet + '/transactions', params={'next': txnJson['next-token'], "limit": 10000})
    txnJson = txnResponse.json()
    
    for getTxn in txnJson['transactions']:
        if getTxn['id'] not in txnDB and txnCurrent == 'false':
            newTxnIDs.insert(0, getTxn['id'])
            getTxn.update({'wallet' : wallet})
            txnDB.update({getTxn['id']: getTxn})
            asaCheck = str(ACSVFunc.asaIDCheck(getTxn, asaDB, asaFetchList))
            if asaCheck != '': asaFetchList.append(asaCheck)
        elif getTxn['id'] in txnDB and txnCurrent == 'false':
            txnCurrent = 'true'



#newTxnIDs list will be in chronological order.
#add each txn to the main txnOrder list.
#collecting ordered chunks and adding the whole chunk will
#keep the chronological ordering in the main txnOrder list
#through multiple executions.
for newID in newTxnIDs:
    txnOrder.append(newID)

print('txnDB current')
txnDB.update({'txnOrder' : txnOrder})
ACSVFunc.saveDB(txnDB, 'resources/txnDB')
txnCountDelta = len(txnOrder) - prerunTxnCount
print('added : ' + str(txnCountDelta) + ' txns to txnDB.')

#------------# Asa DB
#MOVE TO FUNCTIONS
#Solved in older iterations of AlgoCSV
#Implement later in process

for asaID in asaFetchList:
    print('Requesting info - ASA ID: ' + str(asaID))
    asaDB.update({asaID: ACSVFunc.asaRequest(asaID)})

ACSVFunc.saveDB(asaDB, 'resources/asaDB')

#------------# Transaction Checking


#Check txns for identifying details.
print('checking txns - main pass (Quick)')
workingGroup = ''
newGroupCount = 0
tinymanPools = []   #track tinyman pool addressess. This can help define pool bootstrap txns much faster
recheck = []    #use infomation gathered in the first pass to help on a second pass.
for txnID in txnOrder:  #check each txn in chronological order
    txnRaw = txnDB[txnID] #load txn instance
    txnDetails = ACSVFunc.txnTypeDetails(txnRaw) #and txn sub-type specific details

        
    #Group IDs
    if 'group' in txnRaw:
        groupDef = ACSVFunc.groupIDCheck(txnRaw, wallet, addressDB, appDB, groupDB) #check txn for group defining specifics
        if txnRaw['group'] not in groupDB:  #NEW Group ID
            workingGroup = txnRaw['group']  #track current group ID
            if groupDef != '':  #if group can be defined by this txn
                groupDB[txnRaw['group']] = groupDef
                newGroupCount += 1
                if 'Tinyman' in groupDef: #Save Tinyman related addressess.
                    if txnRaw['sender'] != wallet:
                        tinymanPools.append(txnRaw['sender'])
            else:
                recheck.append(txnID)   #add txn to recheck list for quick second pass.
        if groupDef != '' and not isinstance(groupDef, str): #if groupDef is not blank or str, it is a list
            groupDB[txnRaw['group']] = groupDef     #ensure up to date definition is store. overwrite string with list but not vice-versa


freshDB = 'False'
print('checking groups - second pass (Quick)')      #second pass, uses databases built on first pass to define groups not returning enough information initially.
                                                    #manual checks are time consuming, this attempts to reduce the amount of manual scans required.
for txnID in recheck:
    txnRaw = txnDB[txnID]
    txnDetails = ACSVFunc.txnTypeDetails(txnRaw)
    if txnRaw['group'] not in groupDB:              #sometimes 1st txn of a group cannot define it, so it is added to recheck list. then a later txn can define
                                                    #the group. This check filters those out.
        if txnRaw['tx-type'] == 'pay' or txnRaw['tx-type'] == 'axfer':
            if txnDetails['receiver'] in tinymanPools:      #in normal operating conditions, the only unidentified time assets are sent to a pool
                                                            #is during pool bootstrapping. This will catch those txns. just sending assets to a Pool may cause a false positive
                groupDef = ['Tinyman', 'Bootstrap Pool']
                groupDB[txnRaw['group']] = groupDef
                newGroupCount += 1
    if txnRaw['group'] not in groupDB: print('cannot solve: ' + txnRaw['group'])    #This txn cannot be solved after two quick passes.

if newGroupCount > 0: print('added: ' + str(newGroupCount) + ' groups to groupDB')       #if group count increased, report to user. 

ACSVFunc.saveDB(groupDB, 'resources/groupDB')

#------------# Row Building



print('Begin Row Building\n')
#Create CSV file to work with
algocsv = open('ALGO.csv', 'w', newline='', encoding='utf-8')
writer = csv.writer(algocsv) #row writer object
#Header row/row template
row = ['Type', 'Buy Amount', 'Buy Cur.',
       'Sell Amount', 'Sell Cur.',
       'Fee Amount', 'Fee Cur.',
       'Exchange',  #Title of column. Will contain shortened wallet ID to aid multiwallet.
       'Trade Group',   #Platform. 
       'Comment',   #Txn or Group ID, situational.
       'Date']
writer.writerow(row)
#pack group information into multiRow dict.

multiRow = {'rewards':[],
            'txns':[],
            'date': ''}
workingGroup = ''
firstRow = 'y'
lastRow = 'n'

txnOrder.append('end of list')

for txnID in txnOrder:
    if txnID == 'end of list':
        txnID = txnOrder[0]
        lastRow = 'y'
    
    txnRaw = txnDB[txnID]
    txnDetails = ACSVFunc.txnTypeDetails(txnRaw)
    rewardRow = []
    row = ACSVFunc.txnAsRow(txnRaw, wallet, walletName, groupDB, addressDB, appDB, asaDB)

    ##Participation rewards
    #When sending
    if txnRaw['sender'] == wallet and txnRaw['sender-rewards'] > 0:
        rewardRow = ACSVFunc.rewardsRow(txnRaw['sender-rewards'], walletName, txnRaw, asaDB)
    #When receiving
    if 'receiver' in txnDetails and txnDetails['receiver'] == wallet and txnRaw['receiver-rewards'] > 0:
        rewardRow = ACSVFunc.rewardsRow(txnRaw['receiver-rewards'], walletName, txnRaw, asaDB)
  
    #THIS signifies the end of a group. DO NOT REFERENCE txnRaw here. its the new txn that is not in the group
    if 'group' not in txnRaw or txnRaw['group'] != workingGroup:
        if firstRow != 'y':
            #this row not related to previous group
            #SAVE GROUP ROW HERE-------------------


    ##-------------------------------------------------------
          #HANDLE GROUP TYPES HERE
            if 'groupDef' in multiRow:
                groupDef = multiRow['groupDef']
                
                #Tinyman Group Handling
                if 'Tinyman' in groupDef:
                    multiRow = ACSVFunc.RemoveFeeRow(multiRow, 0)
                    txns = multiRow['txns']
                    if 'Fixed Input' in groupDef[1] and len(txns) == 2: #Needs only 2 txns.
                        multiRow = ACSVFunc.swapRow(multiRow, txns[0], txns[1], 'Fixed Input', 0.3, 'Tinyman')
                    elif 'Fixed Output' in groupDef[1]and len(txns) == 2:
                        multiRow = ACSVFunc.swapRow(multiRow, txns[0], txns[1], 'Fixed Output', 0.3, 'Tinyman')
                    elif 'LP Mint' in groupDef[1]:
                        multiRow = ACSVFunc.lpAdjust(multiRow, 'Mint', 'Tinyman')
                    elif 'LP Burn' in groupDef[1]:
                        multiRow = ACSVFunc.lpAdjust(multiRow, 'Burn', 'Tinyman')
                    elif 'Redeem slippage' in groupDef[1]:
                        
                        multiRow = ACSVFunc.slippage(multiRow, txns[0], 'Tinyman', 'Pooled')
                #Pact, currently unsure how to tell fixed end and fee rate
                elif 'Pact' in groupDef:
                    txns = multiRow['txns']
                    if 'Trade' in groupDef and len(txns) == 2: #Needs only 2 txns.
                        multiRow = ACSVFunc.swapRow(multiRow, txns[0], txns[1], 'Fixed Input', 0.0, 'Pact')#0 fees until i can tell which is which
                    elif 'LP Mint' in groupDef[1]:
                        multiRow = ACSVFunc.lpAdjust(multiRow, 'Mint', 'Pact')
                    elif 'LP Burn' in groupDef[1]:
                        multiRow = ACSVFunc.lpAdjust(multiRow, 'Burn', 'Pact')
                #AlgoFi. unsure of swap fees currently
                elif 'AlgoFi' in groupDef:
                    txns = multiRow['txns']
                    if 'Fixed Input' in groupDef:
                        if len(txns) == 2:
                            multiRow = ACSVFunc.swapRow(multiRow, txns[0], txns[1], 'Fixed Input', 0.0, 'AlgoFi')
                        else: print(len(txns))
                    if 'Fixed Output' in groupDef:
                        multiRow = ACSVFunc.swapRow(multiRow, txns[0], txns[1], 'Fixed Output', 0.0, 'AlgoFi')
                        multiRow = ACSVFunc.slippage(multiRow, txns[2], 'AlgoFi', 'Trade')
                    if 'LP Mint' in groupDef:
                        multiRow = ACSVFunc.lpAdjust(multiRow, 'Mint', 'AlgoFi')
                    if 'LP Burn' in groupDef:
                        multiRow = ACSVFunc.lpAdjust(multiRow, 'Burn', 'AlgoFi')
                    if 'Zap' in groupDef:
                        multiRow = ACSVFunc.zap(multiRow)


                    if 'Mint to Collateral' in groupDef:
                        multiRow = ACSVFunc.escrowTxn(multiRow, 0, 'AlgoFi - Collateral', str('AlgoFi: ' + groupDef[2]))
                    elif 'Remove Collateral Underlying' in groupDef:
                        multiRow = ACSVFunc.escrowTxn(multiRow, 0, 'AlgoFi - Collateral', str('AlgoFi: ' + groupDef[2]))
                    elif 'Borrow' in groupDef:
                        multiRow = ACSVFunc.escrowTxn(multiRow, 0, 'AlgoFi - Lending', str('AlgoFi: ' + groupDef[2]))
                    elif 'Repay Borrow' in groupDef:
                        multiRow = ACSVFunc.escrowTxn(multiRow, 0, 'AlgoFi - Lending', str('AlgoFi: ' + groupDef[2]))
                    elif 'Claim Rewards' in groupDef:
                        stakingRow = txns[0]
                        stakingRow[0] = 'Staking'
                        stakingRow[8] = 'AlgoFi: Rewards'
                        multiRow['groupRows'] = [stakingRow]                        


                        
                #AlgoDex.        
                elif 'AlgoDex' in groupDef:
                    #print(groupDef)
                    #print(multiRow)
                    txns = multiRow['txns']
                    if 'Take Order - Buy' in groupDef:
                        multiRow = ACSVFunc.swapRow(multiRow, txns[1], txns[0], 'Take Order', 0.0, 'AlgoDex')
                        if 'Close' not in groupDef:
                            multiRow = ACSVFunc.RemoveFeeRow(multiRow, 2)
                    elif 'Take Order - Sell' in groupDef:
                        multiRow = ACSVFunc.swapRow(multiRow, txns[0], txns[1], 'Take Order', 0.0, 'AlgoDex')
                        if 'Close' not in groupDef:
                            multiRow = ACSVFunc.RemoveFeeRow(multiRow, 2)
                    elif 'Make Sell' in groupDef[1]:
                        multiRow = ACSVFunc.escrowTxn(multiRow, 0, 'AlgoDex - Escrow', 'AlgoDex: Make Order')
                        multiRow = ACSVFunc.escrowTxn(multiRow, 1, 'AlgoDex - Escrow', 'AlgoDex: Make Order')
                    elif 'Make Buy' in groupDef[1]:
                        multiRow = ACSVFunc.escrowTxn(multiRow, 0, 'AlgoDex - Escrow', 'AlgoDex: Make Order')
                    elif 'Cancel Buy' in groupDef[1]:
                        multiRow = ACSVFunc.escrowTxn(multiRow, 0, 'AlgoDex - Escrow', 'AlgoDex: Cancel Order')
                    elif 'Cancel Sell' in groupDef[1]:
                        multiRow = ACSVFunc.escrowTxn(multiRow, 0, 'AlgoDex - Escrow', 'AlgoDex: Cancel Order')
                        multiRow = ACSVFunc.escrowTxn(multiRow, 1, 'AlgoDex - Escrow', 'AlgoDex: Cancel Order')
                    elif 'Order Taken' in groupDef[1]:
                        if multiRow ['groupID'] in algodexTakenDB:
                            multiRow = algodexTakenDB[multiRow['groupID']]
                        else:
                            multiRow = ACSVFunc.algoDexOrderTaken(multiRow, txnDB, groupDB, asaDB, wallet)
                            algodexTakenDB[multiRow['groupID']] = multiRow

                #Yieldly, the 10000 pound flamingo
                elif 'Yieldly' in groupDef:
                    txns = multiRow['txns']
                    if 'Deposit' in groupDef:
                        multiRow = ACSVFunc.escrowTxn(multiRow, 0, 'Yieldly', str('Yieldly: ' + groupDef[2]))
                    elif 'Withdrawal' in groupDef:
                        multiRow = ACSVFunc.escrowTxn(multiRow, 0, 'Yieldly', str('Yieldly: ' + groupDef[2]))
                        if len(txns) == 2:
                            #teal3 pools
                            multiRow = ACSVFunc.RemoveFeeRow(multiRow, 1)
                    elif 'Claim' in groupDef:
                        claimRows = 0
                        for txn in txns:
                            claimRows += 1
                            #print(claimRows)
                            #print(txn)
                            if txn[0] == 'Withdrawal':
                                multiRow = ACSVFunc.RemoveFeeRow(multiRow, (claimRows - 1))
                            elif txn[0] == 'Deposit':
                                txn[0] = 'Staking'
                                txn[8] = 'Yieldly: Rewards'

                        multiRow['groupRows'] = multiRow['txns']
                    elif 'Close T3' in groupDef:
                        if len(txns) == 1:
                            stakingRow = txns[0]
                            stakingRow[0] = 'Staking'
                            stakingRow[8] = 'Yieldly: Rewards'
                            multiRow['groupRows'] = [stakingRow]
                        if len(txns) == 2:
                            stakingRow = txns[0]
                            stakingRow[0] = 'Staking'
                            stakingRow[8] = 'Yieldly: Rewards'
                            multiRow['groupRows'] = [stakingRow]
                            multiRow = ACSVFunc.escrowTxn(multiRow, 1, 'Yieldly', 'Yieldly: Rewards')
                        if len(txns) > 2:    
                            print('help')
                    elif 'Close T5' in groupDef:
                        stakingRow = txns[1]
                        stakingRow[0] = 'Staking'
                        stakingRow[8] = 'Yieldly: Rewards'
                        multiRow['groupRows'] = [stakingRow]
                        multiRow = ACSVFunc.escrowTxn(multiRow, 0, 'Yieldly', 'Yieldly: Rewards')

                #AlgoFund                        
                elif 'AlgoFund' in groupDef:
                    txns = multiRow['txns']
                    
                    if 'Deposit' in groupDef:
                        multiRow = ACSVFunc.escrowTxn(multiRow, 0, 'AlgoFund', str('AlgoFund: ' + groupDef[2]))
                        
                    elif 'Withdrawal' in groupDef:
                        multiRow = ACSVFunc.RemoveFeeRow(multiRow, 0)
                        multiRow = ACSVFunc.escrowTxn(multiRow, 0, 'AlgoFund', str('AlgoFund: ' + groupDef[2]))
                        
                    elif 'Claim' in groupDef:
                        multiRow = ACSVFunc.RemoveFeeRow(multiRow, 0)
                        stakingRow = txns[0]
                        stakingRow[0] = 'Staking'
                        stakingRow[8] = 'AlgoFund: Rewards'
                        multiRow['groupRows'] = [stakingRow]


                #Folks Finance
                elif 'Folks Finance' in groupDef:
                    txns = multiRow['txns']
                    if 'Deposit' in groupDef:
                        txns[0][8] = 'Folks Finance: Deposit'
                        slippage = round(float(txns[1][3]) - float(txns[0][1]), 6)
                        multiRow['groupRows'] = [txns[0]]
                        multiRow = ACSVFunc.escrowTxn(multiRow, 1, 'Folks Finance', str('Folks Finance: ' + groupDef[2]))
                        escrowRow = multiRow['groupRows'][2]
                        escrowRow[1] = round(float(escrowRow[1]) - slippage, 6)
                        multiRow['groupRows'] = [multiRow['groupRows'][0], multiRow['groupRows'][1], escrowRow]
                        
                    elif 'Withdrawal' in groupDef:
                        txns[1][8] = 'Folks Finance: Withdrawal'
                        slippage = round(float(txns[0][1]) - float(txns[1][3]), 6)
                        print(slippage)
                        multiRow['groupRows'] = [txns[1]]
                        multiRow = ACSVFunc.escrowTxn(multiRow, 0, 'Folks Finance', str('Folks Finance: ' + groupDef[2]))
                        escrowRow = multiRow['groupRows'][1]
                        escrowRow[3] = round(float(escrowRow[3]) - slippage, 6)
                        multiRow['groupRows'] = [multiRow['groupRows'][0], escrowRow, multiRow['groupRows'][2]]
                        
                    elif 'Borrow' in groupDef:
                        multiRow = ACSVFunc.escrowTxn(multiRow, 0, 'Folks Finance', str('Folks Finance: ' + groupDef[2]))
                        multiRow = ACSVFunc.escrowTxn(multiRow, 1, 'Folks Finance', str('Folks Finance: ' + groupDef[2]))
                    elif 'Repay' in groupDef:
                        i = 0
                        for txn in txns:
                            if i == 0:
                                stakingRow = txns[0]
                                stakingRow[0] = 'Staking'
                                stakingRow[8] = 'Folks Finance: Rewards'
                                multiRow['groupRows'] = [stakingRow]
                            else:
                                multiRow = ACSVFunc.escrowTxn(multiRow, i, 'Folks Finance', str('Folks Finance: ' + groupDef[2]))
                            i += 1
                        
                    elif 'Increase Borrow' in groupDef:
                        multiRow = ACSVFunc.escrowTxn(multiRow, 0, 'Folks Finance', str('Folks Finance: ' + groupDef[2]))
                        
                    elif 'Reduce Collateral' in groupDef:
                        multiRow = ACSVFunc.escrowTxn(multiRow, 0, 'Folks Finance', str('Folks Finance: ' + groupDef[2]))
                        
                    elif 'Lock & Earn' in groupDef:
                        txns[0][0] = 'Spend'
                        
                        multiRow = ACSVFunc.escrowTxn(multiRow, 0, 'Folks Finance', str('Folks Finance: ' + groupDef[2]))
                        stakingRow = txns[1]
                        stakingRow[0] = 'Staking'
                        stakingRow[8] = 'Folks Finance: Rewards'
                        multiRow['groupRows'] = [txns[0], stakingRow]
                        multiRow = ACSVFunc.escrowTxn(multiRow, 2, 'Folks Finance', str('Folks Finance: ' + groupDef[2]))
                        
                    elif 'Rewards Instant' in groupDef:
                        if len(txns) == 3:
                            stakingRow1 = txns[0]
                            stakingRow2 = txns[1]
                            stakingRow1[0] = 'Staking'
                            stakingRow1[8] = 'Folks Finance: Rewards'
                            stakingRow2[0] = 'Staking'
                            stakingRow2[8] = 'Folks Finance: Rewards'
                            txns[2][0] = 'Spend'
                            txns[2][8] = 'Folks Finance: Rewards'
                            multiRow['groupRows'] = [stakingRow1, stakingRow2, txns[2]]
                        elif len(txns) == 2:
                            stakingRow1 = txns[0]
                            stakingRow1[0] = 'Staking'
                            stakingRow1[8] = 'Folks Finance: Rewards'
                            txns[1][0] = 'Spend'
                            txns[1][8] = 'Folks Finance: Rewards'
                            multiRow['groupRows'] = [stakingRow1, txns[1]]
                        
                    elif 'Rewards Staking' in groupDef:
                        depositFee = txns[0]
                        depositFee[0] = 'Spend'
                        depositFee[8] = 'Folks Finance: Rewards'
                        multiRow['groupRows'] = [depositFee]
                        multiRow = ACSVFunc.escrowTxn(multiRow, 1, 'Folks Finance', str('Folks Finance: ' + groupDef[2]))
                        
                    elif 'Claim' in groupDef:
                        pass #sorry cant do yet, placeholder
                    elif 'Open Account' in groupDef:
                        txns[0][0] = 'Spend'
                        multiRow['groupRows'] = [txns[0]]
                        

                elif 'Akita Inu' in groupDef:
                    txns = multiRow['txns']
                    if 'Token Swap App' in groupDef:
                        multiRow = ACSVFunc.swapRow(multiRow, txns[0], txns[1], 'Token Bridge', 0.0, 'Akita Inu')

                else:
                    pass
                    #----
                    #txns = multiRow['txns']
                    #print(groupDef)
                    #print(multiRow['groupID'])
                    #for txn in txns:
                    #    print(txn)
                    #print('-------')
                    #if 'groupRows' in multiRow:
                    #    for txn in multiRow['groupRows']:
                    #        print(txn)
                    #print('\n')
                    #----

    ##--------------------------------------------------------
            #write group txns to csv
            if 'groupRows' in multiRow:
                groupRows = multiRow['groupRows']
            else: groupRows = multiRow['txns']   
            for gRow in groupRows:
                #if ', ' in str(gRow[8]) and str(gRow[8]) != "['AlgoFi', 'USDC/STBL LP-AFns']":
                #    print(gRow)
                writer.writerow(gRow)
            
            #write rewards from group if any to csv    
            if multiRow['rewards'] != []:
                writer.writerow(multiRow['rewards'])
            #write combined Net Op Fees to csv
            if 'Network Operation Fees' in multiRow:
                netOpFeesRow = ['Spend', '', '',
                multiRow['Network Operation Fees'], 'ALGO', '', '', walletName,
                'Summed Group Network Fees', str('F-' + multiRow['groupID']), multiRow['date']]
                writer.writerow(netOpFeesRow)
            
            #MAKE BLANK GROUP ROW
            multiRow = {'rewards':[],
                        'txns':[],
                        'date': ''}
            
        else: #prevents first row triggering group saving
            firstRow = 'n'

    #txn is part of a group
    if lastRow == 'y':
        break

    
    if 'group' in txnRaw:
        workingGroup = txnRaw['group']
        #pass to function to parse txns types and rewards
        multiRow = ACSVFunc.multiRowProcessing(multiRow, row, txnRaw, groupDB, asaDB, wallet)
        multiRow['groupID'] = txnRaw['group']
        #include any inner txns
        if 'inner-txns' in txnRaw:
            innerTxnList = txnRaw['inner-txns']
            for innerTxn in innerTxnList:
                #pass inner txn to row builder
                innerRow = ACSVFunc.innerTxnRow(innerTxn, wallet, walletName, txnRaw, asaDB, groupDB)
                if isinstance(innerRow, list):
                    #pass inner txn row to group parser
                    multiRow = ACSVFunc.multiRowProcessing(multiRow, innerRow, txnRaw, groupDB, asaDB, wallet)
        #if txnRaw['tx-type'] == 'axfer':
        #    if txnDetails['receiver'] == wallet:
        #        #receive close
        #    elif txnRaw['sender'] == wallet:
                #send close
            
       
    else:
        #Single Row
        #print('\n')

        #write single rows as is to csv.
        if row[8] == 'Network Operation Fees':
            row[0] = 'Spend'
            row[3] = row[5]
            row[4] = 'ALGO'
            row[5] = ''
            row[6] = ''

        
        writer.writerow(row)
        
        if 'inner-txns' in txnRaw:
            innerTxnList = txnRaw['inner-txns']
            for innerTxn in innerTxnList:
                #pass any inner txns to row builder
                innerRow = ACSVFunc.innerTxnRow(innerTxn, wallet, walletName, txnRaw, asaDB, groupDB)
                if isinstance(innerRow, list):
                    #write any inner txns rows to csv
                    writer.writerow(innerRow)
        if rewardRow != []:
            #write rewards row to csv
            writer.writerow(rewardRow)        
    #if 'group' not in txnRaw and ', ' in str(row[8]):
    #    print(row)

    
ACSVFunc.saveDB(algodexTakenDB, 'resources/algodexTakenDB')
algocsv.close()
print('\n')
print('Job Done!')
