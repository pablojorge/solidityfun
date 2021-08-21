import sys
import json
import requests
import subprocess
import traceback

import argparse

## Client

class RPCRequest:
    def __init__(self, host, port, method, params):
        self.host = host
        self.port = port
        self.method = method
        self.params = params

    def get_data(self):
        return {
            "jsonrpc" : "2.0",
            "method" : self.method,
            "params" : self.params,
            "id": 1
        }

    def execute(self):
        resp = requests.post(
            "http://%s:%s" % (self.host, self.port),
            headers={"Content-Type": "application/json"},
            data=json.dumps(self.get_data()),
        )

        if resp.status_code != 200:
            raise Exception(resp.text)

        body = json.loads(resp.text)

        if body.get("error"):
            raise Exception(body['error'])

        return body["result"]

    def as_curl(self):
        return (f"curl -X POST " + 
                f"--data '{json.dumps(self.get_data())}' " +
                f"--header 'Content-Type: application/json' " +
                f"http://{self.host}:{self.port}")

class Client:
    def __init__(self, host, port, verbose):
        self.host = host
        self.port = port
        self.verbose = verbose

    def __call(self, method, params):
        req = RPCRequest(self.host, self.port, method, params)
        if self.verbose:
            print(">>", req.as_curl())
        res = req.execute()
        if self.verbose:
            print("<<", dumps(res))
        return res

    def eth_accounts(self):
        return self.__call("eth_accounts", [])

    def personal_sendTransaction(self, from_, to_, gas, gasPrice, data):
        req = {
            "from": from_,
            "to": to_,
            "gas": hex(gas),
            "gasPrice": hex(gasPrice),
            "data": data
        }
        return self.__call("personal_sendTransaction", [req, ""])

    def eth_call(self, to_, data, at_):
        req = {
            "to": to_,
            "data": data
        }
        return self.__call("eth_call", [req, at_])

    def eth_getTransactionReceipt(self, txhash):
        return self.__call("eth_getTransactionReceipt", [txhash])

    def eth_getLogs(self, address, fromBlock, toBlock, topics):
        req = {
            "address": address,
            "fromBlock": fromBlock,
            "toBlock": toBlock,
            "topics": topics
        }
        return self.__call("eth_getLogs", [req])

    def trace_transaction(self, txhash):
        return self.__call("trace_transaction", [txhash])

## Utils

def dumps(obj):
    return json.dumps(obj, indent="  ")

def remove_0x(string_):
    if string_.startswith("0x"):
        return string_[2:]
    return string_

def prepend_0x(string_):
    if not string_.startswith("0x"):
        return "0x" + string_
    return string_

def zeropad(str_, size):
    return "0" * (size - len(str_)) + str_

def compile(filename):
    cmd = ["solc", filename, "--bin"]

    proc = subprocess.run(cmd, capture_output=True, encoding='utf8')

    if proc.returncode:
        sys.stderr.write(proc.stderr)
        proc.check_returncode()

    return prepend_0x([x for x in proc.stdout.split('\n') if x][-1])

def deploy_contract(client, sender, code):
    txhash = client.personal_sendTransaction(sender, None, 1000000, 10000, code)
    receipt = client.eth_getTransactionReceipt(txhash)
    if receipt["status"] != "0x1":
        raise Exception("Deployment failed")
    return receipt["contractAddress"]

def contract_send_tx(client, sender, contractAddress, data):
    txhash = client.personal_sendTransaction(sender, contractAddress, 4000000, 10000, data)
    receipt = client.eth_getTransactionReceipt(txhash)
    if receipt["status"] != "0x1":
        raise Exception("Sending TX to contract failed")
    return receipt

def contract_call(client, contractAddress, data):
    return client.eth_call(contractAddress, data, "latest")

## Tests

def test_extra_parameter(client):
    code = compile("src/TestToken.sol")
    sender = client.eth_accounts()[0]
    contractAddress = deploy_contract(client, sender, code)

    # Call transfer() including an extra parameter, with a different value:
    receipt = contract_send_tx(client, sender, contractAddress, 
        "0xa9059cbb" 
          "000000000000000000000000aabbccddeeff112233445566778899aabbccddee"
          "0000000000000000000000000000000000000000000000000000000000000010"
          "0000000000000000000000000000000000000000000000000000000000000021")

    # Fetch the token balance of the destination
    balance = contract_call(client, contractAddress, 
        "0x70a08231"
          "000000000000000000000000aabbccddeeff112233445566778899aabbccddee")

    # It should be the value sent in the extra param:
    assert balance == prepend_0x(zeropad('21', 64)), f"Balance is {balance}"

def test_extra_log_data(client):
    token_code = compile("src/TestToken.sol")
    proxy_code = compile("src/ProxyContract.sol")
    sender = client.eth_accounts()[0]
    token_address = deploy_contract(client, sender, token_code)
    proxy_address = deploy_contract(client, sender, proxy_code)

    # Fund proxy contract with some tokens
    contract_send_tx(client, sender, token_address, 
        "0xa9059cbb" +
          zeropad(remove_0x(proxy_address), 64) +
          "0000000000000000000000000000000000000000000000000000000000002000")

    # Submit tx to send from proxy to dummy address
    submit_receipt = contract_send_tx(client, sender, proxy_address, 
        "0xc6427474" +
          zeropad(remove_0x(token_address), 64) +
          "0000000000000000000000000000000000000000000000000000000000000000"
          "0000000000000000000000000000000000000000000000000000000000000060"
            "0000000000000000000000000000000000000000000000000000000000000044"
            "a9059cbb"
            "000000000000000000000000aabbccddeeff112233445566778899aabbccddee"
            "0000000000000000000000000000000000000000000000000000000000000ead")

    # Exec tx in proxy:
    exec_receipt = contract_send_tx(client, sender, proxy_address, "0x0eb288f1")

    # Check final address token balance:
    balance = contract_call(client, token_address, 
        "0x70a08231"
          "000000000000000000000000aabbccddeeff112233445566778899aabbccddee")

    assert balance == prepend_0x(zeropad('ead', 64)), f"Balance is {balance}"

def run_tests(client, tests):
    errors = []

    for test in tests:
        try:
            sys.stdout.write(f"Running '{test.__name__}'... ")
            test(client)
            sys.stdout.write("OK\n")
        except Exception as e:
            _, _, tb = sys.exc_info()
            errors.append((test, e, tb))
            sys.stdout.write(f"ERROR\n")

    for (test, exc, tb) in errors:
        print(f"\nError in {test.__name__}: {exc}\n")
        traceback.print_tb(tb)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("host")
    parser.add_argument("port", type=int)
    parser.add_argument("--verbose", action="store_true", default=False)
    args = parser.parse_args()

    client = Client(args.host, args.port, args.verbose)

    run_tests(client, [
        test_extra_parameter,
        test_extra_log_data
    ])


if __name__ == '__main__':
    main()
