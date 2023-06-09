import ape
import pytest
from eth_hash.auto import keccak

AMOUNT = 10**21
METADATA = "Hello, World!"
SCRIPT = b"\xde\xad\xbe\xef"
DIGEST = keccak(keccak(METADATA.encode()) + keccak(SCRIPT))
CREATION_TIME = None


@pytest.fixture(scope="module", autouse=True)
def setup(alice, chain, start_vote_bounty, token_mock):
    global CREATION_TIME

    token_mock.approve(start_vote_bounty, 2**256 - 1, sender=alice)
    receipt = start_vote_bounty.openBounty(
        token_mock,
        AMOUNT,
        METADATA,
        SCRIPT,
        sender=alice,
        value=start_vote_bounty.OPEN_BOUNTY_COST(),
    )
    CREATION_TIME = receipt.timestamp

    chain.mine(512)

    start_vote_bounty.commitCloseBounty(CREATION_TIME, token_mock, DIGEST, sender=alice)


def test_apply_close_bounty_success(alice, chain, start_vote_bounty, token_mock):
    chain.mine(196)

    eth_balance = alice.balance
    token_balance = token_mock.balanceOf(alice)

    receipt = start_vote_bounty.applyCloseBounty(CREATION_TIME, token_mock, DIGEST, sender=alice)
    identifier = start_vote_bounty.calculateIdentifier(
        alice, CREATION_TIME, token_mock, METADATA, SCRIPT
    )

    # storage
    assert start_vote_bounty.getRewardAmount(identifier) == 0

    # event
    apply_close_bounty_event = next(iter(start_vote_bounty.ApplyCloseBounty.from_receipt(receipt)))
    assert apply_close_bounty_event.identifier == identifier

    # interactions
    assert token_mock.balanceOf(alice) == token_balance + AMOUNT
    assert alice.balance == eth_balance + start_vote_bounty.OPEN_BOUNTY_COST()


def test_apply_close_bounty_fails_invalid_bounty(bob, start_vote_bounty, token_mock):
    with ape.reverts():
        start_vote_bounty.applyCloseBounty(CREATION_TIME, token_mock, DIGEST, sender=bob)


@pytest.mark.parametrize("delta", [64, 512])
def test_apply_close_bounty_fails_invalid_time(alice, chain, delta, start_vote_bounty, token_mock):
    chain.mine(delta)

    with ape.reverts():
        start_vote_bounty.applyCloseBounty(CREATION_TIME, token_mock, DIGEST, sender=alice)
