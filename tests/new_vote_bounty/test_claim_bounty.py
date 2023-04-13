import ape
import pytest
from ape.exceptions import ContractLogicError
from eth_hash.auto import keccak

AMOUNT = 10**21
METADATA = "Hello, World!"
SCRIPT = b"\xde\xad\xbe\xef"
DIGEST = keccak(keccak(METADATA.encode()) + keccak(SCRIPT))
CREATION_TIME = None


@pytest.fixture(scope="module", autouse=True)
def setup(alice, new_vote_bounty, token_mock):
    global CREATION_TIME

    token_mock.approve(new_vote_bounty, 2**256 - 1, sender=alice)
    receipt = new_vote_bounty.openBounty(
        token_mock, AMOUNT, METADATA, SCRIPT, sender=alice, value=new_vote_bounty.OPEN_BOUNTY_COST()
    )
    CREATION_TIME = receipt.timestamp


def test_claim_bounty_success(
    alice,
    bob,
    get_block_header_rlp,
    get_receipt_proof_rlp,
    new_vote_bounty,
    token_mock,
    voting_mock,
):
    receipt = voting_mock.new_vote(METADATA, SCRIPT, sender=bob)
    header_rlp = get_block_header_rlp(receipt.block_number)
    index, proof_rlp = get_receipt_proof_rlp(receipt.txn_hash)

    receipt = new_vote_bounty.claimBounty(
        alice, CREATION_TIME, token_mock, DIGEST, index, header_rlp, proof_rlp, sender=bob
    )
    identifier = new_vote_bounty.calculateIdentifier(
        alice, CREATION_TIME, token_mock, METADATA, SCRIPT
    )

    # storage
    assert new_vote_bounty.getRewardAmount(identifier) == 0
    assert new_vote_bounty.getRefundAmount(alice) == new_vote_bounty.OPEN_BOUNTY_COST()

    # event
    claim_bounty_event = next(iter(new_vote_bounty.ClaimBounty.from_receipt(receipt)))

    assert claim_bounty_event.identifier == identifier
    assert claim_bounty_event.claimant == bob
    assert claim_bounty_event.voteId == 0

    # interactions
    assert token_mock.balanceOf(new_vote_bounty) == 0
    assert token_mock.balanceOf(bob) == AMOUNT


def test_claim_bounty_fails_invalid_bounty(
    alice,
    bob,
    get_block_header_rlp,
    get_receipt_proof_rlp,
    new_vote_bounty,
    token_mock,
    voting_mock,
):
    receipt = voting_mock.new_vote(METADATA, SCRIPT, sender=bob)
    header_rlp = get_block_header_rlp(receipt.block_number)
    index, proof_rlp = get_receipt_proof_rlp(receipt.txn_hash)

    with ape.reverts():
        receipt = new_vote_bounty.claimBounty(
            alice, CREATION_TIME, token_mock, b"", index, header_rlp, proof_rlp, sender=bob
        )


def test_claim_bounty_fails_submitting_old_proof(
    alice,
    bob,
    get_block_header_rlp,
    get_receipt_proof_rlp,
    new_vote_bounty,
    token_mock,
    voting_mock,
):
    token_mock.approve(new_vote_bounty, 2**256 - 1, sender=bob)
    token_mock.transfer(bob, AMOUNT, sender=alice)

    receipt = voting_mock.new_vote(METADATA, SCRIPT, sender=alice)
    header_rlp = get_block_header_rlp(receipt.block_number)
    index, proof_rlp = get_receipt_proof_rlp(receipt.txn_hash)

    receipt = new_vote_bounty.openBounty(
        token_mock, AMOUNT, METADATA, SCRIPT, sender=bob, value=new_vote_bounty.OPEN_BOUNTY_COST()
    )
    created_at = receipt.timestamp

    with ape.reverts():
        receipt = new_vote_bounty.claimBounty(
            bob, created_at, token_mock, DIGEST, index, header_rlp, proof_rlp, sender=alice
        )


def test_claim_bounty_fails_submitting_failed_proof(
    alice,
    bob,
    get_block_header_rlp,
    get_receipt_proof_rlp,
    new_vote_bounty,
    token_mock,
):
    try:
        bob.transfer(token_mock, 1)
    except ContractLogicError as err:
        receipt = err.txn.receipt

    header_rlp = get_block_header_rlp(receipt.block_number)
    index, proof_rlp = get_receipt_proof_rlp(receipt.txn_hash)

    with ape.reverts():
        receipt = new_vote_bounty.claimBounty(
            alice, CREATION_TIME, token_mock, DIGEST, index, header_rlp, proof_rlp, sender=bob
        )


def test_claim_bounty_fails_start_vote_log_not_found(
    alice,
    bob,
    get_block_header_rlp,
    get_receipt_proof_rlp,
    new_vote_bounty,
    token_mock,
):
    receipt = bob.transfer(alice, 1)
    header_rlp = get_block_header_rlp(receipt.block_number)
    index, proof_rlp = get_receipt_proof_rlp(receipt.txn_hash)

    with ape.reverts():
        receipt = new_vote_bounty.claimBounty(
            alice, CREATION_TIME, token_mock, DIGEST, index, header_rlp, proof_rlp, sender=bob
        )