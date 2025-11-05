import threading

import grpc
import banks_pb2
import banks_pb2_grpc

class Branch(banks_pb2_grpc.BankServicer):

    def __init__(self, id, balance, branches):
        # unique ID of the Branch
        self.id = id
        # replica of the Branch's balance
        self.balance = balance
        # the list of process IDs of the branches
        self.branches = branches
        # the list of Client stubs to communicate with the branches
        self.stubList = list()
        # a list of received messages used for debugging purpose
        self.recvMsg = list()
        # iterate the processID of the branches

        self.server = None

    # Set server after starting
    def set_server(self, server):
        self.server = server

    # Stop server method
    def stop_server(self):
        if self.server:
            self.server.stop(1.0)
            print(f'Branch ID {self.id} stopped')

    def Shutdown(self, request, context):
        threading.Thread(target=self.stop_server, daemon=True).start()
        return banks_pb2.ShutdownReply(status='success')

    def populateStubList(self):
        for id in self.branches:
            if id == self.id:
                continue
            port = 5000 + id
            channel = grpc.insecure_channel(f'localhost:{port}')
            stub = banks_pb2_grpc.BankStub(channel)
            self.stubList.append(stub)

    def Deposit(self, amount):
        self.balance += amount
        return banks_pb2.MsgReply(id=self.id, balance=self.balance, result='success')
    
    def Withdraw(self, amount):
        self.balance -= amount
        return banks_pb2.MsgReply(id=self.id, balance=self.balance, result='success')

    def Propagate_Deposit(self, amount):
        success = False

        req = banks_pb2.MsgReq(type='branch', id=self.id, interface='deposit', money=amount)
        for stub in self.stubList:
            try:
                response = stub.MsgDelivery(req)
                self.recvMsg.append(response)
                if response.result == 'success':
                    success = True
            except grpc.RpcError:
                success = False

        return success

    def Propagate_Withdraw(self, amount):
        success = False
        req = banks_pb2.MsgReq(type='branch', id=self.id, interface='withdraw', money=amount)
        for stub in self.stubList:
            try:
                response = stub.MsgDelivery(req)
                self.recvMsg.append(response)
                if response.result == 'success':
                    success = True
            except grpc.RpcError:
                success = False
            
        return success
    
    def Query(self):
        return banks_pb2.MsgReply(id=self.id, balance=self.balance, result='success')
    
    # Process requests from both Client and Branch
    def MsgDelivery(self, request, context):
        # Separate logic for customer and branch as customer requests necessitate propagation
        if request.type == 'customer':
            if request.interface == 'deposit':
                self.balance += request.money
                if self.Propagate_Deposit(request.money):
                    status = 'success'
                else:
                    status = 'fail'
                return banks_pb2.MsgReply(id=self.id, balance=self.balance, result=status)
            if request.interface == 'withdraw':
                self.balance -= request.money
                if self.Propagate_Withdraw(request.money):
                    status = 'success'
                else:
                    status = 'fail'
                return banks_pb2.MsgReply(id=self.id, balance=self.balance, result=status)
            if request.interface == 'query':
                return self.Query()
        if request.type == 'branch':
            if request.interface == 'deposit':
                return self.Deposit(request.money)
            if request.interface == 'withdraw':
                return self.Withdraw(request.money)
        return banks_pb2.MsgReply(id=self.id, balance=self.balance, result='fail')