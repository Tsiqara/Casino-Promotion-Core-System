from __future__ import annotations
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

# Constants for game types
SLOT = 'SLOT'
CASINO = 'CASINO'
SPORT = 'SPORT'


@dataclass
class CasinoSystem:
    input_file: str = '/data/transactions.txt'
    output_file: str = '/data/results.txt'
    balances: dict[str, int] = field(default_factory=dict)
    outputs: list[str] = field(default_factory=list)
    win: bool = field(default=True)
    unused_scenarios: deque[list[str]] = field(default_factory=deque)
    deposits: dict[str, int] = field(default_factory=dict)
    slot_bets: dict[str, int] = field(default_factory=dict)
    user_campaigns: dict[str, list[str]] = field(default_factory=dict)

    def get_file_content(self) -> Iterable[str]:
        file_path = Path(self.input_file)
        try:
            with open(file_path, 'r') as file:
                for line in file:
                    yield line.strip()
        except FileNotFoundError:
            raise RuntimeError(f"File not found: {file_path}")

    def make_transactions(self) -> None:
        transactions = self.get_file_content()
        for transaction in transactions:
            if transaction.startswith('register'):
                self.make_registration(transaction)
            elif transaction.startswith('addscenario'):
                self.add_scenario(transaction)
            elif transaction.startswith('deposit'):
                self.make_deposit(transaction)
            elif transaction.startswith('bet'):
                self.make_bet(transaction)
            elif transaction.startswith('balance'):
                self.get_balance(transaction)
        self.save_outputs()

    def make_registration(self, transaction: str) -> None:
        parts = transaction.split()
        if len(parts) != 2:
            raise ValueError("Invalid number of parameters for registration. Format: register <user_id>")

        user_id = parts[1]
        if user_id in self.balances:
            raise ValueError(f"User with ID {user_id} already exists")

        self.balances[user_id] = 0

    def add_scenario(self, transaction: str) -> None:
        parts = transaction.split()
        if len(parts) != 4:
            raise ValueError(
                "Invalid number of parameters for adding scenario. Format: addscenario <prize1> <prize2> <prize3>")

        _, prize1, prize2, prize3 = parts
        self.unused_scenarios.append([prize1, prize2, prize3])

    def make_deposit(self, transaction: str) -> None:
        parts = transaction.split()
        if len(parts) != 3:
            raise ValueError("Invalid number of parameters for making deposit. Format: deposit <user_id> <amount>")

        _, user_id, amount = parts
        amount = int(amount)
        if amount <= 0:
            raise ValueError("Deposit amount must be positive")

        if user_id not in self.balances:
            raise ValueError(f"User {user_id} not registered")

        self.balances[user_id] += amount
        self.deposits[user_id] = self.deposits.get(user_id, 0) + amount
        self.check_campaign_status(user_id)

    def make_bet(self, transaction: str) -> None:
        parts = transaction.split()
        if len(parts) != 4:
            raise ValueError("Invalid number of parameters for bet. Format: bet <user_id> <game> <amount>")

        _, user_id, game, amount = parts
        amount = int(amount)
        if amount <= 0:
            raise ValueError("Bet amount must be positive")

        if user_id not in self.balances:
            raise ValueError(f"User {user_id} not registered")

        if game not in {SLOT, CASINO, SPORT}:
            raise ValueError(f"Invalid game type {game}, should be one of {SLOT}, {CASINO}, {SPORT}")

        if amount <= self.balances[user_id]:
            self.balances[user_id] += amount if self.win else -amount
            self.win = not self.win

        if game == SLOT:
            self.slot_bets[user_id] = self.slot_bets.get(user_id, 0) + amount
            self.check_campaign_status(user_id)

    def get_balance(self, transaction: str) -> None:
        parts = transaction.split()
        if len(parts) != 2:
            raise ValueError("Invalid number of parameters for getting balance. Format: balance <user_id>")

        user_id = parts[1]
        if user_id not in self.balances:
            raise ValueError(f"User {user_id} not registered")

        self.outputs.append(str(self.balances[user_id]))

    def check_campaign_status(self, user_id: str) -> None:
        if user_id not in self.deposits or user_id not in self.slot_bets:
            return

        if user_id not in self.user_campaigns:
            if self.deposits[user_id] >= 100 and self.slot_bets[user_id] >= 50:
                available_campaign = self.unused_scenarios.popleft()
                available_campaign.append('1')
                self.user_campaigns[user_id] = available_campaign
                self.balances[user_id] += int(available_campaign[0])
        else:
            campaign = self.user_campaigns[user_id]
            if self.deposits[user_id] >= 1000 and self.slot_bets[user_id] >= 500 and campaign[-1] == '2':
                self.balances[user_id] += int(campaign[2])
                campaign[:-1].append('3')
                self.user_campaigns[user_id] = campaign
            elif self.deposits[user_id] >= 500 and self.slot_bets[user_id] >= 250 and campaign[-1] == '1':
                self.balances[user_id] += int(campaign[1])
                campaign[:-1].append('2')
                self.user_campaigns[user_id] = campaign

    def save_outputs(self) -> None:
        try:
            file_path = Path(self.output_file)
            with open(file_path, 'w') as file:
                file.writelines(line + '\n' for line in self.outputs)
        except IOError as e:
            raise RuntimeError(f"Error writing to file: {e}")
