"""
Trusted Authority (TA) Module for DPSShare
Implements mock CP-ABE encryption for demonstration purposes

NOTE: This is a DEMONSTRATION implementation only and does NOT provide real cryptographic security.
In production, use proper CP-ABE libraries like charm-crypto or similar.

This module demonstrates:
- System initialization with CP-ABE setup
- Facility registration with PoW verification
- Attribute-based key generation
- Model encryption/decryption with access policies
"""

import hashlib
import json
import pickle
import time
from typing import Dict, List, Tuple, Any
from flask import Flask, request, jsonify
import sys

from dpsshare_security import ProofOfWork


class MockCPABE:
    """Mock CP-ABE encryption system for demonstration"""
    
    @staticmethod
    def setup(security_param: int, facilities: List[str], attributes: List[str]) -> Tuple[str, str]:
        """
        Setup CP-ABE system: Setup(λ, U, A) → (PK, MSK)
        
        Args:
            security_param: Security parameter λ
            facilities: Set of registered facilities U
            attributes: Attribute universe A
            
        Returns:
            (public_key, master_secret_key)
        """
        pk_data = {
            'security_param': security_param,
            'facilities': facilities,
            'attributes': attributes,
            'timestamp': time.time()
        }
        
        public_key = hashlib.sha256(json.dumps(pk_data, sort_keys=True).encode()).hexdigest()
        
        msk_data = {
            'pk': public_key,
            'master_secret': f"MSK_{security_param}_{time.time()}"
        }
        master_secret_key = hashlib.sha256(json.dumps(msk_data, sort_keys=True).encode()).hexdigest()
        
        return public_key, master_secret_key
    
    @staticmethod
    def key_generation(msk: str, facility_id: str, attributes: Dict[str, str]) -> str:
        """
        Generate attribute-based decryption key for facility
        
        Args:
            msk: Master secret key
            facility_id: Unique facility identifier
            attributes: Facility attributes (e.g., {'role': 'hospital', 'region': 'North'})
            
        Returns:
            Secret key for the facility
        """
        key_data = {
            'msk': msk,
            'facility_id': facility_id,
            'attributes': attributes,
            'timestamp': time.time()
        }
        
        secret_key = hashlib.sha256(json.dumps(key_data, sort_keys=True).encode()).hexdigest()
        return secret_key
    
    @staticmethod
    def encrypt(model_data: bytes, pk: str, policy: Dict[str, Any]) -> Dict[str, Any]:
        """
        Encrypt model using CP-ABE: Encrypt(Model, PK, T) → CT
        
        Args:
            model_data: Serialized model
            pk: Public key
            policy: Access policy tree (e.g., {'role': 'hospital', 'region': 'North'})
            
        Returns:
            Ciphertext dictionary
        """
        encryption_key = hashlib.sha256(f"{pk}_{json.dumps(policy, sort_keys=True)}".encode()).digest()
        
        encrypted_data = bytearray()
        for i, byte in enumerate(model_data):
            encrypted_data.append(byte ^ encryption_key[i % len(encryption_key)])
        
        ciphertext = {
            'ct': bytes(encrypted_data),
            'policy': policy,
            'pk': pk,
            'timestamp': time.time()
        }
        
        return ciphertext
    
    @staticmethod
    def decrypt(ciphertext: Dict[str, Any], sk: str, facility_attributes: Dict[str, str]) -> bytes:
        """
        Decrypt ciphertext: Decrypt(CT, SK_user) → Model
        
        Args:
            ciphertext: Encrypted ciphertext
            sk: Facility's secret key
            facility_attributes: Facility's attributes
            
        Returns:
            Decrypted model data or None if access denied
        """
        policy = ciphertext['policy']
        
        policy_satisfied = all(
            facility_attributes.get(attr) == value
            for attr, value in policy.items()
        )
        
        if not policy_satisfied:
            return None
        
        pk = ciphertext['pk']
        encryption_key = hashlib.sha256(f"{pk}_{json.dumps(policy, sort_keys=True)}".encode()).digest()
        
        decrypted_data = bytearray()
        for i, byte in enumerate(ciphertext['ct']):
            decrypted_data.append(byte ^ encryption_key[i % len(encryption_key)])
        
        return bytes(decrypted_data)


class TrustedAuthority:
    """Trusted Authority for DPSShare system initialization and management"""
    
    def __init__(self, security_param: int = 256, pow_difficulty: int = 4):
        """
        Initialize Trusted Authority
        
        Args:
            security_param: Security parameter for CP-ABE
            pow_difficulty: Difficulty for PoW challenges
        """
        self.security_param = security_param
        self.pow_difficulty = pow_difficulty
        self.facilities = []
        self.attributes = ['role', 'region', 'institution_type']
        self.public_key = None
        self.master_secret_key = None
        self.registered_facilities = {}
        self.facility_keys = {}
        self.encrypted_model = None
        
        print(f"\n{'='*70}")
        print(f"[TRUSTED AUTHORITY] Initializing DPSShare System")
        print(f"{'='*70}")
        print(f"[SETUP] Security Parameter: {security_param}")
        print(f"[SETUP] PoW Difficulty: {pow_difficulty}")
        print(f"[SETUP] Attribute Universe: {self.attributes}")
    
    def system_setup(self, num_facilities: int):
        """
        Algorithm 1: System Setup by Trusted Authority
        
        Args:
            num_facilities: Number of facilities to register
        """
        print(f"\n[ALGORITHM 1] System Setup by Trusted Authority")
        print(f"[SETUP] Generating CP-ABE keys...")
        
        self.facilities = [f"facility_{i}" for i in range(num_facilities)]
        
        self.public_key, self.master_secret_key = MockCPABE.setup(
            self.security_param,
            self.facilities,
            self.attributes
        )
        
        print(f"[SETUP] ✓ Public Key (PK) generated: {self.public_key[:32]}...")
        print(f"[SETUP] ✓ Master Secret Key (MSK) secured (confidential)")
        print(f"[SETUP] ✓ Registered {len(self.facilities)} facilities")
        print(f"[SETUP] ✓ System initialization complete")
        
        return self.public_key
    
    def register_facility(self, facility_id: str, nonce: str, attributes: Dict[str, str]) -> Dict[str, Any]:
        """
        Algorithm 2: Facility Registration with Proof-of-Work
        
        Args:
            facility_id: Unique facility identifier
            nonce: PoW solution
            attributes: Facility attributes
            
        Returns:
            Registration result with secret key if successful
        """
        print(f"\n[ALGORITHM 2] Facility Registration with Proof-of-Work")
        print(f"[REGISTRATION] Facility: {facility_id}")
        print(f"[REGISTRATION] Attributes: {attributes}")
        print(f"[REGISTRATION] Verifying PoW challenge...")
        
        pow_valid = ProofOfWork.verify_pow(facility_id, nonce, self.pow_difficulty)
        
        if not pow_valid:
            print(f"[REGISTRATION] ✗ PoW verification failed for {facility_id}")
            return {'success': False, 'error': 'Invalid PoW'}
        
        print(f"[REGISTRATION] ✓ PoW verification passed")
        print(f"[REGISTRATION] Generating attribute-based secret key...")
        
        secret_key = MockCPABE.key_generation(
            self.master_secret_key,
            facility_id,
            attributes
        )
        
        self.registered_facilities[facility_id] = {
            'attributes': attributes,
            'nonce': nonce,
            'registration_time': time.time()
        }
        
        self.facility_keys[facility_id] = {
            'sk': secret_key,
            'attributes': attributes
        }
        
        print(f"[REGISTRATION] ✓ Secret key SK_{facility_id[:10]} issued")
        print(f"[REGISTRATION] ✓ Facility {facility_id} registered successfully")
        
        return {
            'success': True,
            'secret_key': secret_key,
            'public_key': self.public_key,
            'attributes': attributes
        }
    
    def encrypt_and_distribute_model(self, model_weights, access_policy: Dict[str, str]):
        """
        Algorithm 3: Model Distribution with CP-ABE Encryption
        
        Args:
            model_weights: Model to encrypt
            access_policy: Access control policy
        """
        print(f"\n[ALGORITHM 3] Initial Model Distribution and Encryption")
        print(f"[DISTRIBUTION] Access Policy: {access_policy}")
        print(f"[DISTRIBUTION] Encrypting global model using CP-ABE...")
        
        model_data = pickle.dumps(model_weights)
        
        self.encrypted_model = MockCPABE.encrypt(
            model_data,
            self.public_key,
            access_policy
        )
        
        print(f"[DISTRIBUTION] ✓ Model encrypted with CP-ABE")
        print(f"[DISTRIBUTION] ✓ Policy enforced: {access_policy}")
        print(f"[DISTRIBUTION] ✓ Ciphertext CT ready for distribution")
        print(f"[DISTRIBUTION] Model size: {len(model_data)} bytes")
        
        return self.encrypted_model
    
    def get_encrypted_model(self):
        """Get the encrypted model for distribution"""
        return self.encrypted_model
    
    def decrypt_model_for_facility(self, facility_id: str) -> Any:
        """
        Decrypt model for a registered facility
        
        Args:
            facility_id: Facility requesting model
            
        Returns:
            Decrypted model or None if access denied
        """
        if facility_id not in self.facility_keys:
            print(f"[DECRYPTION] ✗ Facility {facility_id} not registered")
            return None
        
        facility_info = self.facility_keys[facility_id]
        
        decrypted_data = MockCPABE.decrypt(
            self.encrypted_model,
            facility_info['sk'],
            facility_info['attributes']
        )
        
        if decrypted_data is None:
            print(f"[DECRYPTION] ✗ Access denied - Policy not satisfied")
            return None
        
        model_weights = pickle.loads(decrypted_data)
        print(f"[DECRYPTION] ✓ Model decrypted for {facility_id}")
        
        return model_weights


api = Flask(__name__)
ta_instance = None


@api.route('/setup', methods=['POST'])
def setup():
    """Initialize TA system"""
    global ta_instance
    data = request.json
    
    num_facilities = data.get('num_facilities', 5)
    pow_difficulty = data.get('pow_difficulty', 4)
    security_param = data.get('security_param', 256)
    
    ta_instance = TrustedAuthority(security_param, pow_difficulty)
    pk = ta_instance.system_setup(num_facilities)
    
    return jsonify({
        'success': True,
        'public_key': pk,
        'pow_difficulty': pow_difficulty
    })


@api.route('/register', methods=['POST'])
def register():
    """Register a facility with PoW verification"""
    global ta_instance
    
    if ta_instance is None:
        return jsonify({'success': False, 'error': 'TA not initialized'}), 400
    
    data = request.json
    facility_id = data.get('facility_id')
    nonce = data.get('nonce')
    attributes = data.get('attributes', {'role': 'hospital', 'region': 'North'})
    
    result = ta_instance.register_facility(facility_id, nonce, attributes)
    
    return jsonify(result)


@api.route('/encrypt_model', methods=['POST'])
def encrypt_model():
    """Encrypt and distribute model"""
    global ta_instance
    
    if ta_instance is None:
        return jsonify({'success': False, 'error': 'TA not initialized'}), 400
    
    data = request.json
    model_weights = pickle.loads(bytes.fromhex(data.get('model_hex')))
    access_policy = data.get('policy', {'role': 'hospital', 'region': 'North'})
    
    encrypted_model = ta_instance.encrypt_and_distribute_model(model_weights, access_policy)
    
    return jsonify({
        'success': True,
        'ciphertext': pickle.dumps(encrypted_model).hex()
    })


@api.route('/get_encrypted_model', methods=['GET'])
def get_encrypted_model():
    """Get encrypted model for distribution"""
    global ta_instance
    
    if ta_instance is None or ta_instance.encrypted_model is None:
        return jsonify({'success': False, 'error': 'No encrypted model available'}), 400
    
    return jsonify({
        'success': True,
        'ciphertext': pickle.dumps(ta_instance.encrypted_model).hex()
    })


@api.route('/decrypt', methods=['POST'])
def decrypt():
    """Decrypt model for a facility"""
    global ta_instance
    
    if ta_instance is None:
        return jsonify({'success': False, 'error': 'TA not initialized'}), 400
    
    data = request.json
    facility_id = data.get('facility_id')
    
    model_weights = ta_instance.decrypt_model_for_facility(facility_id)
    
    if model_weights is None:
        return jsonify({'success': False, 'error': 'Decryption failed'}), 403
    
    return jsonify({
        'success': True,
        'model': pickle.dumps(model_weights).hex()
    })


@api.route('/health', methods=['GET'])
def health():
    """Health check"""
    return jsonify({
        'status': 'healthy',
        'ta_initialized': ta_instance is not None
    })


if __name__ == '__main__':
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 9600
    print(f"\n[TRUSTED AUTHORITY] Starting TA server on port {port}")
    api.run(host='127.0.0.1', port=port, debug=False, threaded=True)
