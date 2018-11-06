from ryu.base import app.manager
from ryu.ofproto import ofproto_v1_3
from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER, CONFIG_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet

class ExampleSwitch(app_manager.RyuApp):
    *** example switch.***

    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self,*args, **kwargs):
        super(ExampleSwitch, self).__init__(*args, **kwargs)

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        ofp_parser = datapath.ofproto_parser

        # install the table-miss flow entry
        match = ofp_parser.OFPMatch()
        actions = [ofp_parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
                                              ofproto.OFPCML_NO_BUFFER)]
        self.add_flow(datapath, 0, match, actions)

    def add_flow(self, datapath, priority, match, actions):
        #add a flow entry, and install it into datapath
        ofproto = datapath.ofproto
        ofp_parser = datapath.ofproto_parser

        # contruct a flow_mod msg and sent it.
        inst = [ofp_parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
                                                 actions)]
        mod = ofp_parser.OFPFlowMod(datapath=datapath, priority=priority,
                                    match=match, instructions=inst)

        datapath.send_msg(mod)


    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, ev):
        msg =ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        ofp_parser = datapath.ofproto_parser

        # get datapath id to identify Openflow switch.
        dpid = datapath.id
        self.mac_to_port.setdefault(dpid,{})

        # store the info.
        # parser and analysis the received packets.
        pkt = packet.Packet(msg.data)
        eth_pkt = pkt.get_protocol(ethernet.ethernet)
        dst = eth_pkt.dst
        src = eth_pkt.src
        in_port = msg.match['in_port']

        self.logger.info('packet in %s %s %s %s', dpid, src, dst, in_port)

        # learn a src mac address to avoid Flood next time.
        self.mac_to_port[dpid][src] = in_port

        # if the dst mac address has already learned.
        # decide which port to send the packets, otherwise, flood.
        if dst in self.mac_to_port[dpid]:
            out_port = self.mac_to_port[dpid][dst]
        else:
            out_port = ofproto.OFPP_FLOOD

        # contruct actions
        actions = [ofp_parser.OFPActionOutput(out_port)]

        # install a flow mod msg
        if out_port != ofproto.OFPP_FLOOD:
            match = ofp_parser.OFPMatch(in_port=in_port, eth_dst=dst)
            self.add_flow(datapath,1,match,actions)

        # send a packet out.
        out = ofp_parser.OFPPacketOut(
            datapath=datapath, buffer_id=msg.buffer_id, in_port=in_port,
            actions=actions)
        datapath.send_msg(out)















