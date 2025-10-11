from typing import List, Tuple, Dict

def compute_settlement(net_map: Dict[str, float]) -> List[Tuple[str, str, float]]:
    """
    Calculate minimal settlement transfers using greedy algorithm.
    
    Args:
        net_map: Dictionary mapping person_code to net amount
                 (positive = should receive, negative = should pay)
    
    Returns:
        List of tuples (from_code, to_code, amount) representing transfers
    """
    creditors = [(code, amount) for code, amount in net_map.items() if amount > 0.01]
    debtors = [(code, -amount) for code, amount in net_map.items() if amount < -0.01]
    
    creditors.sort(key=lambda x: x[1], reverse=True)
    debtors.sort(key=lambda x: x[1], reverse=True)
    
    transfers = []
    i = j = 0
    
    while i < len(debtors) and j < len(creditors):
        debtor_code, debtor_amount = debtors[i]
        creditor_code, creditor_amount = creditors[j]
        
        payment = round(min(debtor_amount, creditor_amount), 2)
        
        if payment > 0:
            transfers.append((debtor_code, creditor_code, payment))
        
        debtor_amount -= payment
        creditor_amount -= payment
        
        if debtor_amount <= 0.01:
            i += 1
        else:
            debtors[i] = (debtor_code, debtor_amount)
            
        if creditor_amount <= 0.01:
            j += 1
        else:
            creditors[j] = (creditor_code, creditor_amount)
    
    return transfers
