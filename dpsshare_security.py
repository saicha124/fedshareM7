"""
DPSShare Security Module
Implements Proof-of-Work, Digital Signatures, and Validator Committee mechanisms

NOTE: This is a simplified implementation for research/demonstration purposes.
In a production system:
- Keys should be generated using proper cryptographic key generation (not deterministic hashing)
- Private keys should be securely stored and never derived from public identifiers
- A proper Public Key Infrastructure (PKI) should be used
- Consider using standard libraries like PyCrypto, cryptography, or similar

This implementation demonstrates the security workflow and protocol flow
as described in the DPSShare algorithm documentation.
"""
import hashlib
import hmac
import json
import random
import time
from typing import List, Dict, Any, Tuple


class ProofOfWork:
    """Implements Proof-of-Work challenge for Sybil attack prevention"""
    
    @staticmethod
    def compute_pow(facility_id: str, difficulty: int = 4) -> Tuple[str, float]:
        """
        Solve PoW challenge: H(nonce || facility_id) < Target
        
        Args:
            facility_id: Unique identifier for the facility
            difficulty: Number of leading zeros required in hash
            
        Returns:
            (nonce, computation_time)
        """
        target = '0' * difficulty
        nonce = 0
        start_time = time.time()
        
        while True:
            data = f"{nonce}||{facility_id}"
            hash_result = hashlib.sha256(data.encode()).hexdigest()
            
            if hash_result.startswith(target):
                computation_time = time.time() - start_time
                return str(nonce), computation_time
            
            nonce += 1
    
    @staticmethod
    def verify_pow(facility_id: str, nonce: str, difficulty: int = 4) -> bool:
        """
        Verify PoW solution
        
        Args:
            facility_id: Unique identifier for the facility
            nonce: Proposed solution
            difficulty: Number of leading zeros required
            
        Returns:
            True if valid, False otherwise
        """
        target = '0' * difficulty
        data = f"{nonce}||{facility_id}"
        hash_result = hashlib.sha256(data.encode()).hexdigest()
        return hash_result.startswith(target)


class DigitalSignature:
    """Implements simplified digital signature for authentication"""
    
    @staticmethod
    def generate_key(facility_id: str) -> str:
        """Generate a signing key based on facility ID"""
        return hashlib.sha256(f"secret_key_{facility_id}".encode()).hexdigest()
    
    @staticmethod
    def sign(data: bytes, signing_key: str) -> str:
        """
        Sign data using HMAC-SHA256
        
        Args:
            data: Data to sign
            signing_key: Secret signing key
            
        Returns:
            Signature as hex string
        """
        return hmac.new(
            signing_key.encode(),
            data,
            hashlib.sha256
        ).hexdigest()
    
    @staticmethod
    def verify(data: bytes, signature: str, signing_key: str) -> bool:
        """
        Verify signature
        
        Args:
            data: Original data
            signature: Signature to verify
            signing_key: Secret signing key
            
        Returns:
            True if signature is valid
        """
        expected_signature = DigitalSignature.sign(data, signing_key)
        return hmac.compare_digest(signature, expected_signature)


class ValidatorCommittee:
    """Implements validator committee with consensus voting"""
    
    def __init__(self, num_validators: int = 3):
        """
        Initialize validator committee
        
        Args:
            num_validators: Number of committee members
        """
        self.num_validators = num_validators
        self.validators = [f"validator_{i}" for i in range(num_validators)]
        self.validator_keys = {
            v: DigitalSignature.generate_key(v) for v in self.validators
        }
    
    def validate_share(self, share_data: bytes, signature: str, facility_id: str) -> Dict[str, Any]:
        """
        Validate a share through committee consensus
        
        Args:
            share_data: The share data to validate
            signature: Digital signature from facility
            facility_id: ID of the submitting facility
            
        Returns:
            Dictionary with validation results
        """
        facility_key = DigitalSignature.generate_key(facility_id)
        
        sig_valid = DigitalSignature.verify(share_data, signature, facility_key)
        if not sig_valid:
            return {
                "approved": False,
                "reason": "Invalid signature",
                "votes": {}
            }
        
        votes = {}
        for validator in self.validators:
            vote = self._validator_vote(share_data, signature)
            votes[validator] = vote
        
        total_votes = sum(votes.values())
        required_votes = (self.num_validators // 2) + 1
        approved = total_votes >= required_votes
        
        return {
            "approved": approved,
            "votes": votes,
            "total_votes": total_votes,
            "required_votes": required_votes,
            "reason": "Consensus reached" if approved else "Insufficient votes"
        }
    
    def _validator_vote(self, share_data: bytes, signature: str) -> int:
        """
        Simulate individual validator vote
        Returns 1 (valid) or 0 (invalid)
        """
        basic_checks = len(share_data) > 0 and len(signature) > 0
        
        random_factor = random.random() > 0.05
        
        return 1 if (basic_checks and random_factor) else 0
    
    def sign_approved_share(self, share_data: bytes) -> str:
        """
        Committee signs an approved share
        
        Args:
            share_data: The approved share data
            
        Returns:
            Committee signature
        """
        committee_key = DigitalSignature.generate_key("committee_master")
        return DigitalSignature.sign(share_data, committee_key)
    
    @staticmethod
    def verify_committee_signature(share_data: bytes, signature: str) -> bool:
        """
        Verify committee signature
        
        Args:
            share_data: The share data
            signature: Committee signature to verify
            
        Returns:
            True if valid
        """
        committee_key = DigitalSignature.generate_key("committee_master")
        return DigitalSignature.verify(share_data, signature, committee_key)


class FogNodeSecurity:
    """Security mechanisms for fog node authentication"""
    
    @staticmethod
    def sign_partial_model(model_data: bytes, fog_node_id: str) -> str:
        """
        Fog node signs its partial aggregated model
        
        Args:
            model_data: Serialized model data
            fog_node_id: ID of the fog node
            
        Returns:
            Digital signature
        """
        fog_key = DigitalSignature.generate_key(f"fog_{fog_node_id}")
        return DigitalSignature.sign(model_data, fog_key)
    
    @staticmethod
    def verify_fog_signature(model_data: bytes, signature: str, fog_node_id: str) -> bool:
        """
        Verify fog node signature
        
        Args:
            model_data: Serialized model data
            signature: Signature to verify
            fog_node_id: ID of the fog node
            
        Returns:
            True if valid
        """
        fog_key = DigitalSignature.generate_key(f"fog_{fog_node_id}")
        return DigitalSignature.verify(model_data, signature, fog_key)


def demonstrate_security_features():
    """Demonstrate all security features"""
    print("=" * 70)
    print("DPSShare Security Module Demonstration")
    print("=" * 70)
    
    facility_id = "hospital_001"
    print(f"\n1. Proof-of-Work (PoW) Challenge")
    print(f"   Facility ID: {facility_id}")
    print(f"   Computing PoW with difficulty=4...")
    nonce, comp_time = ProofOfWork.compute_pow(facility_id, difficulty=4)
    print(f"   ✓ PoW solved! Nonce: {nonce}, Time: {comp_time:.4f}s")
    print(f"   ✓ Verification: {ProofOfWork.verify_pow(facility_id, nonce, 4)}")
    
    print(f"\n2. Digital Signature Authentication")
    test_data = b"test_model_weights"
    signing_key = DigitalSignature.generate_key(facility_id)
    signature = DigitalSignature.sign(test_data, signing_key)
    print(f"   Data: {test_data}")
    print(f"   Signature: {signature[:32]}...")
    print(f"   ✓ Verification: {DigitalSignature.verify(test_data, signature, signing_key)}")
    
    print(f"\n3. Validator Committee Consensus")
    committee = ValidatorCommittee(num_validators=5)
    print(f"   Committee size: {committee.num_validators} validators")
    result = committee.validate_share(test_data, signature, facility_id)
    print(f"   ✓ Approved: {result['approved']}")
    print(f"   ✓ Votes: {result['total_votes']}/{result['required_votes']} required")
    print(f"   ✓ Reason: {result['reason']}")
    
    if result['approved']:
        committee_sig = committee.sign_approved_share(test_data)
        print(f"   ✓ Committee signature: {committee_sig[:32]}...")
        print(f"   ✓ Committee sig valid: {ValidatorCommittee.verify_committee_signature(test_data, committee_sig)}")
    
    print(f"\n4. Fog Node Security")
    fog_node_id = "fog_server_0"
    fog_signature = FogNodeSecurity.sign_partial_model(test_data, fog_node_id)
    print(f"   Fog Node: {fog_node_id}")
    print(f"   Signature: {fog_signature[:32]}...")
    print(f"   ✓ Verification: {FogNodeSecurity.verify_fog_signature(test_data, fog_signature, fog_node_id)}")
    
    print("\n" + "=" * 70)
    print("All security mechanisms operational!")
    print("=" * 70)


if __name__ == "__main__":
    demonstrate_security_features()
