### Import Python modules
import argparse
import os
import requests
import xmlschema
from datetime import datetime as dt
import xmlsec
from lxml import etree
import subprocess
import pytz
from OpenSSL import crypto
import re
import locale
from tkinter import messagebox
from cryptography import x509
from cryptography.hazmat.backends import default_backend
### Own modules
from Instance_Manager import IM
from Logger import myLogger
from Global import Sensor_Name_dict

# Load instances
EB = IM.get_instance("EB")
CC = IM.get_instance("CC")
MD = IM.get_instance("MD")
logger = IM.get_instance("logger")

# Initialize logger
log_path_validation = r"DCCvalidation.log"
validationlog = myLogger.getLogger("validationlog", log_path_validation)
logger.info(f"Logger for the DCC-Validation has been initialized.")

# Global variables
ca_issuer = "D-TRUST CA 5-22-2 2022"
root_ca_file = "D-TRUST Root CA 5 2022"
oid = "1.3.6.1.4.1.59749.1"

############################################
#####        General Functions         #####
############################################
def store_pem_cert(cert, filename):
    with open(filename, "w") as f:
        f.write(cert)

def parse_xml(xml_file_path):
    try:
        tree = etree.parse(xml_file_path)
        root = tree.getroot()
        return root
    except Exception as e:
        validationlog.warning(f"Failed to parse XML: {e}")
        return None
    
##########################################
##    Functions for schema validation   ##
##########################################
def fetch_schema(url, local_path):
    """Fetches the schema from the given URL and saves it locally."""    
    validationlog.info(f"Fetching schema from {url}...")
    response = requests.get(url)
    if response.status_code == 200:
        with open(local_path, 'wb') as f:
            f.write(response.content)
            validationlog.info(f"Fetched schema from {url} and saved to {local_path}")
    else:
        validationlog.warning(f"Failed to fetch schema from {url}: {response.status_code}")
        print(f"Failed to fetch schema from {url}: {response.status_code}")
        return False
    return True
 
def validate_xml(xml_file, xsd_file):
    try:
        schema = xmlschema.XMLSchema(xsd_file)
        validationlog.info(f"Schema '{xsd_file}' loaded successfully.")
        schema.validate(xml_file)
        validationlog.info(f"XML is valid:{schema.is_valid(xml_file)}")
        schema_is_valid = schema.is_valid(xml_file)
        if schema_is_valid:
            return True
        else:
            try:
                schema.validate(xml_file)
            except xmlschema.XMLSchemaValidationError as e:
                validationlog.warning(f"Error executing the validate(xml) function. Error: {e}")
                print(f"XML-Error: {e}")
            return False
    except Exception as e:
        print(f"Error: {e}")
        validationlog.info(f"Error: {e}")
        return False

##################################################
## Functions for digital signature verification ##
##################################################
def get_signature_details(xml_file):
    '''Extracts the certificate and signing time from an XML file with a digital signature.'''
    # Define namespaces to simplify XPath queries
    ns = {
        'dsig': 'http://www.w3.org/2000/09/xmldsig#',
        'xades': 'http://uri.etsi.org/01903/v1.3.2#',
        'ecdsa': 'http://www.w3.org/2001/04/xmldsig-more#',
        'xsi': 'http://www.w3.org/2001/XMLSchema-instance'
    }
    root = parse_xml(xml_file)
    # Find the Signature element
    signature_node = xmlsec.tree.find_node(root, xmlsec.constants.NodeSignature, namespace=ns['dsig'])
    if signature_node is None:
        validationlog.error("Signature element not found.")
        return None

    # Extract signing time
    signing_time_node = signature_node.xpath('.//xades:SigningTime', namespaces=ns)
    if not signing_time_node:
        validationlog.warning("Signing time element not found.")
        signing_date = "Unknown"
    else:
        signing_date = signing_time_node[0].text
        print(f"Signing date: {signing_date}")

    # Extract certificate (assuming it's in a X509Certificate node for simplicity, adjust if necessary)
    x509_certificate_node = signature_node.xpath('.//dsig:X509Certificate', namespaces=ns)
    if not x509_certificate_node:
        validationlog.warning("X509Certificate element not found.")
        return None    

    seal_cert_pem = f"-----BEGIN CERTIFICATE-----\n{x509_certificate_node[0].text.strip()}\n-----END CERTIFICATE-----"
    return seal_cert_pem, signing_date, signature_node


def validate_xml_signature(signature_node, seal_cert_pem):
    '''Validates the signature of an XML file using a given certificate.'''
    if signature_node is None:
        validationlog.info("Signature element not found.")
        return False

    # Create a digital signature context
    dsig_ctx = xmlsec.SignatureContext()

    # Setup the key and other necessary things before verification
    try:
        key = xmlsec.Key.from_memory(seal_cert_pem, xmlsec.KeyFormat.CERT_PEM)
        dsig_ctx.key = key

        # Validate the signature
        dsig_ctx.verify(signature_node)
        validationlog.info("Signature is valid. That means the DCC has not been chaged since it was signed.")
        return True
    except xmlsec.VerificationError:
        validationlog.info("Signature is invalid. The DCC has been changed since it was signed.")
        return False
    except Exception as e:
        validationlog.error(f"An error occurred during signature verification: {e}")
        return False

def extract_certificate_dates(seal_cert_pem):
    try: 
        result = subprocess.run(['openSSL', 'x509', '-in', 'seal_cert.pem', '-noout', '-dates'], capture_output=True, text=True)
        output = result.stdout.splitlines()
        not_before = output[0].split('=')[1].strip() if 'notBefore' in output[0] else None
        not_after = output[1].split('=')[1].strip() if 'notAfter' in output[1] else None
        return not_before, not_after
    except subprocess.TimeoutExpired:
        validationlog.warning("The openssl command timed out.")
        return None, None
    except Exception as e:
        validationlog.error(f"An unexpected error occurred: {e}")
        return None, None

#########################################################
## Functions for certificate authenticity and validity ##
#########################################################

def check_signing_date(seal_cert_pem, signing_date_str):
    not_before_str, not_after_str = extract_certificate_dates(seal_cert_pem)
    if not not_before_str or not not_after_str:
        validationlog.warning("Failed to retrieve valid date ranges from the certificate.")
        return False

    # Retrieve current locale settings
    current_locale = locale.getlocale()
    # Set locale to 'en_US' for consistent date parsing
    if current_locale[0] != "en_US":
        locale.setlocale(locale.LC_TIME, "en_US")

    # Convert date strings to datetime objects
    not_before = dt.strptime(not_before_str, '%b %d %H:%M:%S %Y %Z')
    not_after = dt.strptime(not_after_str, '%b %d %H:%M:%S %Y %Z')
    signing_date = dt.strptime(signing_date_str, '%Y-%m-%dT%H:%M:%SZ')

    # Convert all dates to UTC
    not_before = pytz.utc.localize(not_before)
    not_after = pytz.utc.localize(not_after)
    signing_date = pytz.utc.localize(signing_date)

    # Check if the signing date is within the certificate's validity period
    if not_before <= signing_date <= not_after:
        return True
    else:
        validationlog.info("When the DCC was signed/sealed the certificate was not valid!")
        return False

def check_authenticity(cert, dcc_xml, ns):
    """Checks if the issuer in the certificate matches the issuer in the DCC XML."""
    dcc_signer_xml = dict(cert.get_subject().get_components())[b'O'].decode("utf-8")
    dcc_issuer_xml = dcc_xml.xpath('//dcc:calibrationLaboratory/dcc:contact/dcc:name/dcc:content/text()', namespaces=ns)[0]
    dcc_issuer_cetificate = str(dcc_issuer_xml)
    dcc_issuer_cetificate = dcc_issuer_cetificate.split(",")[0]
    if dcc_signer_xml in dcc_issuer_cetificate:
        return True
    else:
        return False

def verify_certificate_signature(cert_file, issuer_cert, root_cert, signing_date):
    """
    Verifies a certificate up to the root and checks the certificate chain.

    :param cert_file: End-entity certificate
    :param root_cert: Root CA certificate
    :param intermediate_certs: PEM file or list of PEM files with intermediate certificates
    :param signing_date: Time of validation in ISO format ‘YYYY-MM-DDTHH:MM:SSZ’
    :return: True/False
    """
    datetime = dt.strptime(signing_date, '%Y-%m-%dT%H:%M:%SZ')
    unixtime = int(datetime.timestamp())
    cmd = [
        "openssl", "verify",  # Invoke the OpenSSL verification command
        "-attime", f"{unixtime}",  # Perform the verification as if it were at the given UNIX timestamp
        "-CAfile", root_cert,  # Root CA certificate used as trust anchor
        "-untrusted", issuer_cert,  # Intermediate certificate (issuer certificate) supplied for chain building
        cert_file  # End-entity certificate to be verified
        ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        if "OK" in result.stdout:
            validationlog.info(f"✅ Signature from {cert_file} is valid")
            return True
        else:
            validationlog.warning(f"❌ Signature from {cert_file} is invalid:\n{result.stdout}")
            return False
    except subprocess.CalledProcessError as e:
        validationlog.error(f"❌ Error during digital signature verification: {e.stderr}")
        return False

#--- Möglicherweise überflüssig -----------------------------------------------------------------------------------
def download_cert(url, filename):
    """Downloads a certificate from a URL and saves it locally."""
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        with open(filename, "wb") as f:
            f.write(response.content)
        validationlog.info(f"📥 Certificate from {url} saved as {filename}")
        return filename
    except requests.RequestException as e:
        validationlog.warning(f"❌ Error downloading certificate from {url}: {e}")
        return None

def convert_der_to_pem(der_file, pem_file):
    """Converts a DER certificate to PEM."""
    import shutil
    if shutil.which("openssl") is None:
        print("⚠️ OpenSSL not found!")
        validationlog.warning("⚠️ OpenSSL not found!")
        return None

    try:
        cmd = ["openssl", "x509", "-inform", "DER", "-in", der_file, "-out", pem_file]
        subprocess.run(cmd, check=True)
        os.remove(der_file)  # Delete the DER file after conversion
        validationlog.info(f"🔄 Converted {der_file} → {pem_file}")
        return pem_file
    except subprocess.CalledProcessError:
        validationlog.warning(f"❌ Error converting {der_file} to PEM.")
        return None

def extract_ocsp_info(cert_file):
    """Reads OCSP URL and issuer certificate from a PEM certificate."""
    with open(cert_file, "rb") as f:
        cert = x509.load_pem_x509_certificate(f.read(), default_backend())

    # Extract OCSP-URL
    ocsp_url = None
    issuer_url = None
    try:
        aia = cert.extensions.get_extension_for_class(x509.AuthorityInformationAccess)
        for access_desc in aia.value:
            if access_desc.access_method == x509.OID_OCSP:
                ocsp_url = access_desc.access_location.value
            elif access_desc.access_method == x509.OID_CA_ISSUERS:
                issuer_url = access_desc.access_location.value
        return ocsp_url, issuer_url
    except x509.ExtensionNotFound:
        validationlog.warning("⚠️ No AIA-extension found.")
        return None, None


def verify_certificate(cert_file, issuer_cert, ocsp_url, root_ca, signing_date):
    """
    Verifies the validity of a certificate using OCSP (Online Certificate Status Protocol) via OpenSSL.
    Args:
        cert_file (str): Path to the certificate file to be verified.
        issuer_cert (str): Path to the issuer's certificate file.
        ocsp_url (str): URL of the OCSP responder.
        root_ca (str): Path to the root CA certificate file.
        signing_date (str): The signing date in ISO 8601 format (e.g., 'YYYY-MM-DDTHH:MM:SSZ').
    Returns:
        bool: True if the certificate is valid ("good" status), False otherwise (revoked, unknown, or error).
    Logs:
        - Logs the result of the OCSP check (valid, revoked, unknown, or error) using the validationlog logger.
    Raises:
        None. All exceptions are handled internally and result in a False return value.
    """
    datetime = dt.strptime(signing_date, '%Y-%m-%dT%H:%M:%SZ')
    unixtime = int(datetime.timestamp())
    cmd = [
        "openssl", "ocsp", "-attime", f"{unixtime}",
        "-issuer", issuer_cert,
        "-cert", cert_file,
        "-url", ocsp_url,
        "-CAfile", root_ca,
        "-text"
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        output = result.stdout
        if "Cert Status: good" in output:
            validationlog.info("✅ Certificate is valid")
            return True
        elif "Cert Status: revoked" in output:
            validationlog.warning("❌ Certificate is revoked")
            return False
        elif "Cert Status: unknown" in output:
            validationlog.warning("❓ Certificatestatus is unknown")
            return False
        else:
            validationlog.warning("⚠️ No clear answer received from OCSP responder")
            return False

    except subprocess.CalledProcessError as e:
        validationlog.error(f"Error during OCSP verification: {e.stderr}")
        return False


def find_root_cert(cert_file):
    """ Extrahiert den Subject-Namen des letzten Zertifikats in einer PEM-Datei. """
    try:
        with open(cert_file, 'rb') as f:
            cert_data = f.read()
        cert = crypto.load_certificate(crypto.FILETYPE_PEM, cert_data)
        root = cert.get_issuer().CN
    except Exception as e:
        validationlog.error(f"Error loading certificate: {e}")
        return None
    if root == root_ca_file:
        validationlog.info(f"Root found: {root}")
        return root
    else:
        root_path = f"{root}.pem"
        print(f"Repeated call of find_root_cert with root_path: {root_path}")
        return find_root_cert(root_path)
    

def get_oid_from_cert(cert_pem):
    # Load the certificate with pyOpenSSL
    cert = crypto.load_certificate(crypto.FILETYPE_PEM, cert_pem)
    
    for i in range(cert.get_extension_count()):
        ext = cert.get_extension(i)
        ext_name = ext.get_short_name().decode("utf-8")
        
        try:
            ext_data = ext.__str__()  # Does not always work, therefore raw data as a fallback
        except:
            ext_data = ext.get_data().decode("latin1", errors="ignore")  # Convert binary data to string

        # Extract OID with Regex
        match = re.search(r"(\d+\.\d+\.\d+\.\d+\.\d+\.\d+\.\d\d\d\d\d+\.\d)", ext_data)
        if match:
            return match.group(1)
    
    return None  # In Case no OID was found
    
#########################################################
##   Functions for checking the calibration interval   ##
#########################################################

def check_calibration_intervall(recalibrationIntervall, signing_date):
    today = dt.now().date()
    signing_date = dt.strptime(signing_date, '%Y-%m-%dT%H:%M:%SZ').date()
    recalibrationIntervall = int(recalibrationIntervall)
    since_last_calibration = (today - signing_date).days / 30
    if since_last_calibration < recalibrationIntervall:
        return True
    else:
        return False
   

############################################
##     Functions for DCC validation       ##
############################################

def performDCCvalidation(filepath, mode, id=None):
    ####################### Setup and check, which sensors are connected #######################
    validationlog.info(f"-------------------- Validation startet at: {dt.now()} --------------------")
    EB.publish("DCC_schema_validation_update", {"Message": "New DCC received.", "value": None, "led": []})
    CC.update_connected_sensors()
    DCCconnected = CC.get_connected_sensors()
    print(f"Connected sensors: {DCCconnected}")
    if not all(DCCconnected):
        validationlog.warning("Not all sensors are connected.")
    if all(not sensor for sensor in DCCconnected):
        validationlog.warning("All sensors are disconnected.")
        sensors_connected = False
        EB.publish("DCC_schema_validation_update", {"Message": "System not connected. Just validating.", "value": None, "led": []})
    else:
        sensors_connected = True

    operation_mode = mode
    validationlog.info(f"Operation mode: {operation_mode}")

    ####################### Loading the DCC #######################
    dcc_xml = parse_xml(filepath)
    if dcc_xml is None:
        EB.publish("DCC_schema_validation_update", {"Message": "DCC couldn't be parsed. No validation possible! \n --------------- Validation aborted ---------------", "value": False, "led": [i for i in range(7)]})
        return
    # NameSpace:
    ns = {
        'dsig': 'http://www.w3.org/2000/09/xmldsig#',
        'xades': 'http://uri.etsi.org/01903/v1.3.2#',
        'ecdsa': 'http://www.w3.org/2001/04/xmldsig-more#',
        'xsi': 'http://www.w3.org/2001/XMLSchema-instance',
        'dcc': "https://ptb.de/dcc",
        'si': "https://ptb.de/si"
    }

    ################## Check whether DCC belongs to one of the connected sensors ##################
    try:
        sensorName = dcc_xml.xpath('//dcc:identification[@refType="temp_DUTProbeID" or @refType="basic_marking"]/dcc:value/text()', namespaces=ns)[0]
    except:
        validationlog.warning(f"No Tag with name found. Do you have the wrong version of template?")
        EB.publish("DCC_schema_validation_update", {"Message": "No sensor name found in the DCC. DCC is not processed further.\n --------------- Vadiation aborted ---------------", "value": None, "led": [i for i in range(7)]})
        return
    
    EB.publish("DCC_schema_validation_update", {"Message": f"DCC for '{sensorName}'. Validating...", "value": None, "led": []})

    if id is None: # Drag and Drop case
        if sensorName in Sensor_Name_dict.values():
            belongs_to_the_four = True
            if sensors_connected:
                key = [k for k, v in Sensor_Name_dict.items() if v == sensorName][0]
                id = int(key.split(" ")[-1])-1
                if DCCconnected[id]: # One of the four AND sensor is connected
                    dcc_belongs_to_connected_sensor = True
            else: # One of the four AND sensor is not connected
                dcc_belongs_to_connected_sensor = False
        else:
            belongs_to_the_four = False
            dcc_belongs_to_connected_sensor = False
        
    else: # Switch case
        belongs_to_the_four = True
        if sensors_connected and DCCconnected[id]: # One of the four AND sensor is connected
            dcc_belongs_to_connected_sensor = True
        else: # One of the four AND sensor is not connected
            dcc_belongs_to_connected_sensor = False

    ################## Schema validation ##################
    schemal_location = dcc_xml.xpath("//@xsi:schemaLocation", namespaces=ns)[0]
    schemal_location = schemal_location.split(" ")[1]
    xsd_file_path = os.path.basename(schemal_location)
 
    # Determine the schema file path
    try:
        schema = fetch_schema(schemal_location, xsd_file_path)
    except Exception as e:
            validationlog.error(f"Failed to fetch the schema from the URL. Error: {e}")
            EB.publish("DCC_schema_validation_update", {"Message": "Failed to fetch the schema from the URL. DCC is not processed.\n ------------------------- Validation aborted -------------------------", "value": None, "led": [i for i in range(7)]})
            return    
    
    SchemaVAL = validate_xml(filepath, xsd_file_path)

    if SchemaVAL:
        message = f"DCC schema validation passed."
    else:
        message = f"DCC schema violated. DCC cannot be processed.\n ------------------------- Validation aborted -------------------------"

    EB.publish("DCC_schema_validation_update", {"Message": message, "value": SchemaVAL, "led": [0]})


    if SchemaVAL:
        ################## Signature validation ##################
        details = get_signature_details(filepath)
        if details:
            seal_cert_pem, signing_date, signature_node = details
            cert = crypto.load_certificate(crypto.FILETYPE_PEM, seal_cert_pem)
            serial_number = str(cert.get_subject().get_components()[5][1].decode("utf-8"))
            validationlog.info(f"Serialnumber: {serial_number}")
            validationlog.info(f"Signingdate: {signing_date}")
            store_pem_cert(seal_cert_pem, "seal_cert.pem")
            ######## Validation of the signature ########
            signature_is_valid = validate_xml_signature(signature_node, seal_cert_pem)
            if signature_is_valid:
                message = "Data integrity check passed."
            else:
                message = "Seal is broken, DCC is corrupted."
            EB.publish("DCC_schema_validation_update", {"Message": message, "value": signature_is_valid, "led": [1]}) 

#-----------------------------------------------------------------------------------------------------------------------
            ################ Certificate validation ################
            # Download and - if neccesseary convert - all needed certificates
            try:
                oscp_url, issuer_url = extract_ocsp_info("seal_cert.pem")
                validationlog.info(f"OCSP-URL: {oscp_url}, Issuer-Certificate Download URL: {issuer_url}")
            except:
                validationlog.warning("Failed to extract OCSP-URL and Issuer-Certificate-URL from the seal certificate.")
            
            try: # Download issuer-certificate in DER-Format
                download_cert(issuer_url, "D-TRUST CA 5-22-2 2022.crt")
                validationlog.info("Issuer certificate downloaded successfully.")
                # convert_der_to_pem("D-TRUST CA 5-22-2 2022.crt", "D-TRUST CA 5-22-2 2022.pem")
            except:
                validationlog.warning("Failed to download the issuer certificate in DER format.")
            try: # Issuer-Zertifikat in PEM-Format konvertieren
                if not os.path.exists("D-TRUST CA 5-22-2 2022.crt"):
                    validationlog.warning("Issuer certificate in DER format does not exist. Cannot convert to PEM format.")
                else:
                    convert_der_to_pem("D-TRUST CA 5-22-2 2022.crt", "D-TRUST CA 5-22-2 2022.pem")
                    validationlog.info("Issuer certificate converted to PEM format successfully.")
            except:
                validationlog.warning("Failed to convert the issuer certificate to PEM format.")
            
            try:
                root_oscp_url, root_url = extract_ocsp_info("D-TRUST CA 5-22-2 2022.pem")
                validationlog.info(f"Root-OCSP-URL: {root_oscp_url}, Issuer-Zertifikat Download URL: {root_url}")
            except:
                validationlog.warning("Failed to extract OCSP-URL and Root-Certificate-URL from the issuer certificate.")
            try: # Download the root certificate in DER format
                download_cert(root_url, "D-TRUST Root CA 5 2022.crt")
                validationlog.info("Root certificate downloaded successfully.")
                convert_der_to_pem("D-TRUST Root CA 5 2022.crt", "D-TRUST Root CA 5 2022.pem")
                validationlog.info("Root certificate converted to PEM format successfully.")
            except:
                validationlog.warning("Failed to download and convert the root certificate.")

            ######## Verification of the authenticity of the issuer ########
            # Signature valid (checked in the previous step) & Expected issuer (comparison between DCC tag and certificate)
            seal_sig_is_valid = verify_certificate_signature("seal_cert.pem", "D-TRUST CA 5-22-2 2022.pem", "D-TRUST Root CA 5 2022.pem", signing_date) # Schritt 1 in der TSPS (bereits für Siegel, als auch für Ca-Zertifikat)
            
            dcc_issuer_xml = str(dcc_xml.xpath('//dcc:calibrationLaboratory/dcc:contact/dcc:name/dcc:content/text()', namespaces=ns)[0]).split(",")[0]
            issuer_is_authentic = check_authenticity(cert, dcc_xml, ns)
            #TODO: Nummer des Kalibrierlabors mit prüfen
            if seal_sig_is_valid and issuer_is_authentic:
                message = f"DCC authenticity is validated:\n Issued by '{dcc_issuer_xml}'"
            else:
                message = f"DCC authenticity could not be validated. Claimed issuer: '{dcc_issuer_xml}'"
            EB.publish("DCC_schema_validation_update", {"Message": message, "value": issuer_is_authentic, "led": [2]})

            
            ######## Gültigkeit des Zertifikats ########          
            # Verification of seal/signature
            signing_date_is_ok = check_signing_date(seal_cert_pem, signing_date) # Schritt 2 in der TSPS
            validationlog.info(f"signing_date liegt im Gültigkeitsbereich des Siegelzertifikats: {signing_date_is_ok}")
            #TODO Gültigkeitszeitraum vom D Trust Zertifikat überprüfen
            
            cert_is_valid = verify_certificate("seal_cert.pem", "D-TRUST CA 5-22-2 2022.pem", oscp_url, "D-TRUST Root CA 5 2022.pem", signing_date) # Schritt 3 in der TSPS
            #TODO: Überprüfung für D Trust Zertifikat wiederholen
            # Schritt 4 in der TSPS
            issuer = dict(cert.get_issuer().get_components())[b'CN'].decode("utf-8")
            
            if issuer == ca_issuer:
                correct_issuer = True
            else:
                correct_issuer = False

            # Stringvergleich ist hier eigentlich nicht ausreichend
            # Ist dann eigentlich obsolet
            root_subject = find_root_cert("seal_cert.pem")
            # print(f"Root-Subject: {root_subject}")
            
            if root_subject == root_ca_file:
                validationlog.info(f"✅ Die Zertifikatskette endet auf der D-TRUST Root CA 5 2022.")
                correct_root = True
            else:
                validationlog.warning(f"❌ Die Zertifikatskette endet nicht auf der D-TRUST Root CA 5 2022.")
                correct_root = False

            admission_oid = get_oid_from_cert(seal_cert_pem)
            if admission_oid == oid:
                validationlog.info(f"✅ Admission OID {oid} found in the certificate is the right one.")
                oid_is_correct = True
            else:
                validationlog.warning(f"❌ Admission OID {oid} not found in the certificate or it is the wrong one.")
                oid_is_correct = False

            if all((seal_sig_is_valid, issuer_is_authentic, signing_date_is_ok, cert_is_valid, correct_issuer, correct_root, oid_is_correct)):
                validationlog.info("The certificate is valid.")
                is_accredited = True
            else:
                validationlog.info("The certificate is invalid.")
                is_accredited = False

            if is_accredited:
                message = f"Accreditation valid at time of issue:"
            else:
                message = f"DCC is not issued unter an Accreditation"
            EB.publish("DCC_schema_validation_update", {"Message": message, "value": is_accredited, "led": [3]})

            if is_accredited:
                message = f"{serial_number}"
                EB.publish("DCC_schema_validation_update", {"Message": message, "value": None, "led": []})               
        
        else:
            EB.publish("DCC_schema_validation_update", {"Message": "No electronic seal or signature can be recognized on this DCC.\n DCC integrety, issuer authenticity and accreditation could not be verified.", "value": False, "led": [1, 2, 3]})

#-----------------------------------------------------------------------------------------------------------------------
        ################## Display sensor information ##################
        if belongs_to_the_four:
            validationlog.info(f"Name of the {sensorName}")            

            if dcc_belongs_to_connected_sensor:
                message = f"DCC belongs to sensor '{sensorName}'. This probe is connected"
            #TODO: Fall einfügen, dass der Sensor zu den 4 gehört, aber nicht verbunden ist. --> gelbe LED
            else:
                message = f"DCC belongs to sensor '{sensorName}', but the probe is not connected. DCC is not processed."
        else:
            message = "DCC does not belong to one of the possibly connected sensors."
        
        EB.publish("DCC_schema_validation_update", {"Message": message, "value": dcc_belongs_to_connected_sensor, "led": [4]})

        # Calibration Intervall
        try:
            cal_date = dcc_xml.xpath("//dcc:endPerformanceDate/text()", namespaces=ns)[0]
            EB.publish("DCC_schema_validation_update", {"Message": f"The service was conducted on: {cal_date}.", "value": None, "led": None})
        except:
            EB.publish("DCC_schema_validation_update", {"Message": "No calibration date found in the DCC.", "value": None, "led": [5]})

        try:  
            recalibrationIntervall = MD.input_limits_dict["Calibration Intervall"]
            intervall_ok = check_calibration_intervall(recalibrationIntervall, signing_date)
            if intervall_ok:
                message = f"Calibration is within accepted period "
            else:
                message = f"Calibration is expired. Please recalibrate."
            EB.publish("DCC_schema_validation_update", {"Message": message, "value": intervall_ok, "led": [5]})
        except:
            EB.publish("DCC_schema_validation_update", {"Message": "No recalibration intervall set.", "value": None, "led": [5]})

        # Measurement data
        try:
            measurementdata_string = dcc_xml.xpath('//dcc:quantity[contains(@refType, "basic_referenceValue")]//si:realListXMLList[si:unitXMLList="\degreecelsius"]/si:valueXMLList/text()', namespaces=ns)[0]
            
            measurementdata = re.split(" ", measurementdata_string)
            measurementdata = [float(i) for i in measurementdata]
            min_temp = min(measurementdata)
            max_temp = max(measurementdata)

            EB.publish("DCC_schema_validation_update", {"Message": f"The probe was calibrated from {min_temp} °C to {max_temp} °C", "value": None, "led": None})
        except:
            EB.publish("DCC_schema_validation_update", {"Message": "No measurement data found in the DCC.", "value": None, "led": [6]})

        if dcc_belongs_to_connected_sensor or (operation_mode == "Simulation" and belongs_to_the_four):
            print(f"Connected: {dcc_belongs_to_connected_sensor}, belongs_to_the_four: {belongs_to_the_four}, operation_mode: {operation_mode}")
            try:
                if id is None:
                    key = [k for k, v in Sensor_Name_dict.items() if v == sensorName][0]
                    id = int(key.split(" ")[-1])-1
                    
                current_sensor = CC.get_sensors()[id]

                upperLimit = MD.input_limits_dict[f"{current_sensor.get_name()}_Upper Limit"]
                lowerLimit = MD.input_limits_dict[f"{current_sensor.get_name()}_Lower Limit"]

                if min_temp <= lowerLimit and max_temp >= upperLimit:
                    message = "Calibrated range is appropriate for process window."
                    cal_range_fits_process = True
                else:
                    message = "Calibrated range does not cover the process window."
                    cal_range_fits_process = False

                EB.publish("DCC_schema_validation_update", {"Message": message, "value": cal_range_fits_process, "led": [6]})

            except:
                cal_range_fits_process = False
                EB.publish("DCC_schema_validation_update", {"Message": "No limits for this sensor set.", "value": None, "led": [6]})
            
            try:
                EB.publish("min_max_temp_is_set", {"name":current_sensor, "min_temp": min_temp, "max_temp": max_temp})
            except Exception as e:
                validationlog.error(f"Fehler beim veröffentlichen des Events min_max_temp_is_set: {e}")

                
            
            if all((SchemaVAL, signature_is_valid, issuer_is_authentic, is_accredited, intervall_ok, cal_range_fits_process)):
                all_valid = True
                EB.publish("DCC_schema_validation_update", {"Message": "Validation succeeded - DCC is processed for metrological traceability and quality-assured process conformity", "value": None, "led": []})
                Gui = IM.get_instance("Gui")
                Gui.DCCswitsches[id].toggle_var.set(True)
                EB.publish("DCC_included", {"ID": id, "value": Gui.DCCswitsches[id].toggle_var.get(), "filename": filepath})
                EB.publish("DCC_validation_successful", {"ID": id, "value": all_valid})
            else:
                all_valid = False
                EB.publish("DCC_validation_successful", {"ID": id, "value": all_valid})

            if any((SchemaVAL, signature_is_valid, issuer_is_authentic, is_accredited, intervall_ok, cal_range_fits_process)) and not all((SchemaVAL, signature_is_valid, issuer_is_authentic, is_accredited, intervall_ok, cal_range_fits_process)):
                include_dcc = messagebox.askyesno("Validation result", "The received DCC does not fully comply with the systems quality requirements! Do you wish to process it further?")
                if include_dcc:
                    validationlog.info("DCC is going to be included in the measurement.")
                    Gui = IM.get_instance("Gui")
                    Gui.DCCswitsches[id].toggle_var.set(True)
                    EB.publish("DCC_included", {"ID": id, "value": Gui.DCCswitsches[id].toggle_var.get(), "filename": filepath})
                else:
                    validationlog.info("DCC is not going to be included in the measurement.")

        if sensors_connected and belongs_to_the_four and not dcc_belongs_to_connected_sensor:
            messagebox.showinfo(f"Connection status of sensor {sensorName}", "The DCC belongs to a sensor that is not connected. The DCC is not processed further. If you want to use the DCC please connect the sensor and validate again.")
        
    
        EB.publish("DCC_schema_validation_update", {"Message": "------------------------- Validation completed. -------------------------", "value": None, "led": []})
    
    else:
        EB.publish("DCC_schema_validation_update", {"Message": "------------------------- Validation aborted -------------------------.", "value": None, "led": []})

    validationlog.info(f"Validation finished at: {dt.now()}")