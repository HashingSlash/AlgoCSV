# AlgoCSV
A python script to pull the transactions of an Algorand wallet and put them into a CSV file.

Dependancies: Requests

Main features:
Groups: Compress transaction groups down to 1 or 2 rows. Swap shows as 1 txn, not 4. Algofi txns show as 1, not 14-16 txns.
Tinyman: Algo network fees are part of the swap row. Swap Fees (0.3%) are calculated and shown as a separate row.
Algofi: Records Inner transactions. This will show amounts sent from Algofi to you as part of a borrow txn group for example.
Participation Rewards: Parsed out from the TXNs and shown as a separate row.


Limits and issues:
Commenting: code could be commented a LOT better. will work on it. just wanted to push a release for people to use/test. I know it's tax filing time in the U.S. so if it can help you, fantastic.
Platform, ID, GroupID columns need more consistency. This was a failure to plan before building on my behalf. Again, can be improved.
dApp Support: Currently supports Yieldly, Tinyman, Algofi. These are the dApps I have been using and able to test with. I haven't touched AlgoGems, AB2, NFT's, ASA Management, or Govenance so the code doesn't currently support these features. They may be added in the future (I'm signed up for G2, I may get into NFT trading at some point). There is some generic group handling that may catch this stuff but I'm just not sure.


I'm an amateur programmer using this as an exorcise in learning API get requests, so it's not pro-grade by any measure. Also, no tax jurisdiction has been considered. This is not a tax report or financial advice or anything else. This is just a tool that may help you with your record keeping. I make no guarantees. This is my first time using Github too.


Donations: ALGO - SLASHDABBEUIM3ZBALEZCV5UXGF67TXU4H25UU6BILRIMA6EJ4ZJ2BATOM
