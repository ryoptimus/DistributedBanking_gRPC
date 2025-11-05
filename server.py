import sys
import time
import json
import threading
from concurrent import futures

import grpc
import banks_pb2
import banks_pb2_grpc

from branch import Branch

def serve():
    # Check for proper number of args
    if len(sys.argv) != 2:
        print('Error. Must provide the name of one JSON file in the project directory as an argument.')
        return
    
    filename = sys.argv[-1]
    if '.json' not in filename:
        print('Error. Argument must be a JSON file.')
        return
    
    # Open input file and read
    with open(filename) as input_file:
        inputs = json.loads(input_file.read())

    branch_entries = []
    branch_ids = []
    seen_branch_ids = set()

    i = 1
    for input in inputs:
        if input['type'] == 'branch':
            if input['id'] not in seen_branch_ids:
                branch_entries.append(input)
                branch_ids.append(input['id'])
                seen_branch_ids.add(input['id'])
        i += 1

    branches = []
    servers = []

    # Start servers
    for be in branch_entries:
        port = 5000 + be['id']
        branch = Branch(
            id = be['id'],
            balance = be['balance'],
            branches = branch_ids
        )
        branches.append(branch)
        server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
        banks_pb2_grpc.add_BankServicer_to_server(branch, server)
        server.add_insecure_port('[::]:' + str(port))
        server.start()
        print(f'Branch ID {branch.id} listening on port {port}')
        branch.set_server(server)
        servers.append(server)

    time.sleep(1)

    for branch in branches:
        branch.populateStubList()

    # Spawn waiter threads for all servers
    waiters = []
    for s in servers:
        t = threading.Thread(target=s.wait_for_termination, daemon=True)
        t.start()
        waiters.append(t)

    # Block until all servers have actually terminated
    try:
        while any(t.is_alive() for t in waiters):
            time.sleep(0.5)
    # Also include logic for shutdown using ctrl-C just in case
    except KeyboardInterrupt:
        print('Shutting down...')
        for s in servers:
            s.stop(0)

if __name__ == '__main__':
    serve()