import grpc
import banks_pb2
import banks_pb2_grpc

class Customer:
    def __init__(self, id, events):
        # unique ID of the Customer
        self.id = id
        # events from the input
        self.events = events
        # a list of received messages used for debugging purpose
        self.recvMsg = list()
        # pointer for the stub
        self.stub = None

    # Create the Customer stub
    def createStub(self):
        port = 5000 + self.id
        channel = grpc.insecure_channel(f'localhost:{port}')
        self.stub = banks_pb2_grpc.BankStub(channel)

    # Send out the events to the Bank
    def executeEvents(self):
        if self.stub is None:
            self.createStub()
        
        out = []
        for event in self.events:
            if event['interface'] == 'query':
                response = self.stub.MsgDelivery(
                    banks_pb2.MsgReq(
                        type = 'customer',
                        id = self.id,
                        interface = event['interface'],
                        money = 0
                    )
                )
                self.recvMsg.append(response)
                out.append({'interface': 'query', 'balance': int(response.balance)})

            if event['interface'] == 'deposit':
                response = self.stub.MsgDelivery(
                    banks_pb2.MsgReq(
                        type = 'customer',
                        id = self.id,
                        interface = event['interface'],
                        money = event['money']
                    )
                )
                self.recvMsg.append(response)
                out.append({'interface': 'deposit', 'result': response.result})
                
            if event['interface'] == 'withdraw':
                response = self.stub.MsgDelivery(
                    banks_pb2.MsgReq(
                        type = 'customer',
                        id = self.id,
                        interface = event['interface'],
                        money = event['money']
                    )
                )
                self.recvMsg.append(response)
                out.append({'interface': 'withdraw', 'result': response.result})
        return {'id': self.id, 'recv': out}
            