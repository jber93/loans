from dataclasses import dataclass
from datetime import date
from typing import Tuple


@dataclass(init=True, repr=True, eq=True, order=False)
class Cycle:
    period: int
    period_day: float
    incoming_balance: float
    remaining_balance: float
    payment: float
    amortization: float
    interest_payment: float


@dataclass(init=True, repr=True, eq=True, order=True)
class Loan:
    amount: float  # original amount. make a new class for currency
    interest_rate: float
    monthly_fee: float
    loan_type: str
    start_date: date = date.today()
    months: int = None
    amortization_rate: float = None

    def make_payment_plan(
        self,
        # annuity args
        periods: int = None,
        # fixed amort args
    ) -> list:
        """_summary_

        make payment plan class instead

        Args:
            periods (int, optional): _description_. Defaults to None.

        Raises:
            NotImplementedError: _description_

        Returns:
            list: _description_
        """
        payment_plan = []

        if self.loan_type == "annuity":
            # payment plan for annuity
            payment_plan = payment_plan_annuity(
                amount=self.amount,
                interest_rate=self.interest_rate,
                monthly_fee=self.monthly_fee,
                periods=periods or self.months,
            )
        else:
            # payment plan for fixed amortization loans
            raise NotImplementedError

        self.payment_plan_attributes = payment_plan_attributes(payment_plan)
        self.payment_plan = payment_plan
        return payment_plan


def payment_plan_annuity(
    amount: float, interest_rate: float, monthly_fee: float, periods: int
) -> list:
    """Calculate payment plan for an annuity loan.

    TODO:
    - cut off so that last payment is not more than remaining balance

    Args:
        amount (float): _description_
        interest_rate (float): _description_
        monthly_fee (float): _description_
        periods (int): _description_

    Returns:
        list: list of Cycles(s)
    """

    payment_plan = []
    incoming_balance = amount
    r = interest_rate / 12  # monthly rate, or rate per period
    payment = annuity_payment(amount, interest_rate / 12, monthly_fee, periods)
    for j in range(1, periods + 1):
        # this part can probably be abstracted
        interest_payment = r * incoming_balance
        amortization = payment - interest_payment
        remaining_balance = incoming_balance + monthly_fee - payment

        cycle_data = {
            "period": j,
            "period_day": j * (365 / 12),  # month length correction
            "incoming_balance": incoming_balance,
            "remaining_balance": remaining_balance,
            "payment": payment,
            "amortization": amortization,
            "interest_payment": interest_payment,
        }
        payment_plan.append(Cycle(**cycle_data))
        incoming_balance = remaining_balance + interest_payment

    return payment_plan


def annuity_payment(amount: float, rate: float, fee: float, periods: int) -> float:
    """Calculate annuity payment for a loan. An annuity is a series of equal
    payments made at equal intervals.

    Args:
        amount (float): _description_
        rate (float): _description_
        fee (float): _description_
        periods (int): assumed to be months, not sure if it works with other periods

    Returns:
        float: annuity payment
    """
    return (amount * rate) / (1 - (1 + rate) ** -periods) + fee


def calculate_apr(
    payment_plan: list,
    interest_rate: float = 0.05,
    delta: float = 1 * 10**-4,
    threshold_for_diff: float = 0.01,
    max_iterations: int = 10**5,
) -> Tuple[float, float, int]:
    """Calculating annual percentage rate, using European method.

    Source:
    https://eur-lex.europa.eu/LexUriServ/LexUriServ.do?uri=OJ:L:2008:133:0066:0092:EN:PDF

    TODO:
    - not happy with naming for this and "calculate_eir" function

    Args:
        payment_plan (list): _description_
        interest_rate (float, optional): initial guess for . Defaults to 0.05.
        delta (float, optional): _description_. looping step size to 1*10**-4.
        threshold_for_diff (float, optional): Defaults to .01.
        max_iterations (int, optional): Defaults to 10**5.

    Returns:
        tuple: _description_
    """
    loan_amount = sum(cycle.amortization for cycle in payment_plan)
    n = len(payment_plan)

    # init
    diff = 1
    iterations = 0
    i = interest_rate / (n + 1)
    while abs(diff) > threshold_for_diff and iterations <= max_iterations:
        discounted_payments = [
            # denominator is discounting factor
            cycle.payment / (1 + i) ** (cycle.period_day / 365)
            for cycle in payment_plan
        ]
        present_value_of_payments = sum(discounted_payments)

        diff = present_value_of_payments - loan_amount
        # take larger steps if diff is large
        multiplier = 1 + diff / present_value_of_payments
        if diff > 0:
            i += delta * multiplier
        elif diff < 0:
            i -= delta * multiplier
        else:
            # you made it lol
            break

        iterations += 1

    apr = i
    return apr, diff, iterations


def calculate_eir(i: float, compounding_periods: int = 12):
    """Effective interest rate (EIR), taking into account the effect of
    interest compound. Compounding periods per year: monthly->12, quarterly->4.

    Args:
        i (float): interest
        compounding_periods (_type_): _description_

    Returns:
        _type_: _description_
    """
    return (1 + i / compounding_periods) ** compounding_periods - 1


def payment_plan_attributes(payment_plan: list, iteration_kwargs={}, digits=5) -> dict:
    """Calculate attributes for a payment plan.

    Args:
        payment_plan (list): _description_
        iteration_kwargs (dict, optional): options for APR calculation loop

    Returns:
        dict: _description_
    """
    attributes = {}

    periods = len(payment_plan)
    sum_of_payments = sum(cycle.payment for cycle in payment_plan)
    sum_of_amortizations = sum(cycle.amortization for cycle in payment_plan)
    sum_of_interest = sum(cycle.interest_payment for cycle in payment_plan)
    attributes["months"] = periods
    attributes["total_payments"] = sum_of_payments
    attributes["interest_payments"] = sum_of_interest
    attributes["amortizations"] = sum_of_amortizations
    attributes["financing_cost"] = sum_of_payments - sum_of_amortizations

    apr, diff, iterations = calculate_apr(payment_plan, **iteration_kwargs)
    attributes["apr"] = apr
    attributes["eir"] = calculate_eir(apr)

    return {k: round(v, digits) for k, v in attributes.items()}


if __name__ == "__main__":
    d = {
        "amount": 13400,
        "interest_rate": 0.05,
        "monthly_fee": 0,
        "loan_type": "annuity",
    }
    loan = Loan(**d)
    loan.make_payment_plan(periods=3)
    print(loan.payment_plan)
    print(loan.payment_plan_attributes)
