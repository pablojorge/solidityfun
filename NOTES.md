USDC extra data: https://etherscan.io/tx/0x27ed4c07939cffd6bab706904e2b6e4e22c8fdf085bb24802f1dceddb9e8379f

EFI submitTransaction extra data:

https://etherscan.io/tx/0xb13bd31b183497cffc330663335846697f963875923e4c4104f94f8955296833

00: c6427474 // submit
00: 000000000000000000000000656c00e1bcd96f256f224ad9112ff426ef053733 // destination
20: 0000000000000000000000000000000000000000000000000000000000000000 // value
40: 0000000000000000000000000000000000000000000000000000000000000060 // data location
60:   0000000000000000000000000000000000000000000000000000000000000044 // data length (68)
    		a9059cbb // transfer (4 bytes)
    		000000000000000000000000dce65223cd94a95630bbd246667097cc7be26674 // destination (32 bytes)
    		0000000000000000000000000000000000000000000000000de0b6b3a7640000 // value (32 bytes)
    		00000000000000000000000000000000000000000000000000000000 // extra bytes (28 bytes - 32 bytes alignment?)


Confirm and send above tx:

https://etherscan.io/tx/0x3617c87a3e9364d438e1df7eb1fc600a44e32df8535bee9865079d4981c0b07f
https://etherscan.io/vmtrace?txhash=0x3617c87a3e9364d438e1df7eb1fc600a44e32df8535bee9865079d4981c0b07f&type=parity