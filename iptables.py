# coding: utf-8
#
# Floating IP Addresses manager (IPFloater)
# Copyright (C) 2015 - GRyCAP - Universitat Politecnica de Valencia
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
# 
import iptc
import logging
import cpyutils.log

_LOGGER = cpyutils.log.Log("IPT")

def setup_basic_rules():
    table = iptc.Table(iptc.Table.NAT)
    table.refresh()
    table.autocommit = False
    chain_pos = table.create_chain("ipfloater-POSTROUTING")
    chain_pre = table.create_chain("ipfloater-PREROUTING")
    chain_out = table.create_chain("ipfloater-OUTPUT")
    
    # iptables -t nat -A POSTROUTING -m conntrack ! --ctstate DNAT -j ACCEPT
    rule_pos = iptc.Rule()
    rule_pos.create_target("ACCEPT")
    m = rule_pos.create_match("conntrack")
    m.ctstate = "!DNAT"
    chain_pos.append_rule(rule_pos)
        
    link_chains(table, "POSTROUTING", "ipfloater-POSTROUTING")
    link_chains(table, "PREROUTING", "ipfloater-PREROUTING")
    link_chains(table, "OUTPUT", "ipfloater-OUTPUT")
    table.commit()
    table.autocommit = True

def unlink_and_delete_chain(table, chainname):
    linked_chain = None
    if chainname[-7:] == "-OUTPUT":
        linked_chain = "OUTPUT"
    if chainname[-11:] == "-PREROUTING":
        linked_chain = "PREROUTING"
    if chainname[-12:] == "-POSTROUTING":
        linked_chain = "POSTROUTING"
        
    if linked_chain is not None:
        # We suppose that it is linked
        unlink_chains(table, "ipfloater-%s" % linked_chain, chainname)
    
    delete_chain(table, chainname)
    
def cleanup_rules():
    table = iptc.Table(iptc.Table.NAT)
    table.refresh()
    table.autocommit = False
    chains = [ chain.name for chain in table.chains ]
    chains_rules = [ chainname for chainname in chains if (chainname[:10]=="ipfl-rule-")]

    for chainname in chains_rules:
        unlink_and_delete_chain(table, chainname)
    
    unlink_chains(table, "POSTROUTING", "ipfloater-POSTROUTING")
    unlink_chains(table, "PREROUTING", "ipfloater-PREROUTING")
    unlink_chains(table, "OUTPUT", "ipfloater-OUTPUT")
    delete_chain(table, "ipfloater-POSTROUTING")
    delete_chain(table, "ipfloater-PREROUTING")
    delete_chain(table, "ipfloater-OUTPUT")
    
    table.commit()
    table.autocommit = True

def delete_chain(table, chain_name):
    '''
    This function removes the iptables chain with name "chain_name" from the table object addressed by "table".
    If the chain is not in the table, this function does nothing.
    '''
    chains = [ chain.name for chain in table.chains if chain.name == chain_name ]
    if len(chains) > 0:
        chain = iptc.Chain(table, chain_name)
        for rule in chain.rules[:]:
            chain.delete_rule(rule)
        chain.delete()

def link_chains(table, first_chain, second_chain):
    '''
    This function executes an iptables rule that links the chain named "first_chain" to the chain named "second_chain"
    in table "table". At the end, it creates a rule like: iptables -t table.name -A FIRST_CHAIN -j SECOND_CHAIN
    '''
    rule = iptc.Rule()
    rule.target = rule.create_target(second_chain)
    chain = iptc.Chain(table, first_chain)
    chain.append_rule(rule)
    
def unlink_chains(table, first_chain, second_chain):
    '''
    This function executes an iptables rule that unlinks the chain named "first_chain" to the chain named "second_chain"
    in table "table". At the end, it creates a rule like: iptables -t table.name -D FIRST_CHAIN -j SECOND_CHAIN
    '''
    chains = [ chain.name for chain in table.chains if chain.name == first_chain ]
    if len(chains) > 0:
        chain = iptc.Chain(table, first_chain)
        rules = [ rule for rule in chain.rules if rule.target.standard_target == second_chain ]
        for rule in rules:
            chain.delete_rule(rule)

def chain_exists(table, chain_name):
    '''
    This function returns true if the iptables chain named "chain_name" is in table "table"
    '''
    chains = [ chain.name for chain in table.chains if chain.name == chain_name ]
    if len(chains) > 0:
        return True
    else:
        return False

def remove_endpointchains(idendpoint):
    '''
    This method executes the needed funtions to remove the set of iptables rules that will make possible a redirection with the id in idendpoint.
    '''
    table = iptc.Table(iptc.Table.NAT)
    table.refresh()
    table.autocommit = False
    unlink_chains(table, "ipfloater-OUTPUT", "ipfl-rule-%s-OUTPUT" % idendpoint)
    delete_chain(table, "ipfl-rule-%s-OUTPUT" % idendpoint)

    unlink_chains(table, "ipfloater-POSTROUTING", "ipfl-rule-%s-POSTROUTING" % idendpoint)
    delete_chain(table, "ipfl-rule-%s-POSTROUTING" % idendpoint)

    unlink_chains(table, "ipfloater-PREROUTING", "ipfl-rule-%s-PREROUTING" % idendpoint)
    delete_chain(table, "ipfl-rule-%s-PREROUTING" % idendpoint)
    _LOGGER.debug("removing chain for endpoint %s" % idendpoint)
    table.commit()
    table.autocommit = True
    return True