"""
Q-Shield Asset Discovery Engine
Discovers internet-facing assets through various methods.
"""

import asyncio
import ipaddress
import re
import socket
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional, Dict, Set, AsyncIterator
import logging

import aiodns
import aiohttp

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("discovery")


@dataclass
class DiscoveredAsset:
    """Represents a discovered asset."""
    hostname: str
    ip_address: Optional[str] = None
    port: int = 443
    protocol: str = "HTTPS"
    discovery_source: str = "manual"
    asn: Optional[str] = None
    asn_name: Optional[str] = None
    country_code: Optional[str] = None
    cloud_provider: Optional[str] = None
    is_accessible: bool = False
    discovered_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict = field(default_factory=dict)


class DNSResolver:
    """Asynchronous DNS resolution."""
    
    def __init__(self, nameservers: List[str] = None):
        self.nameservers = nameservers or ["8.8.8.8", "8.8.4.4", "1.1.1.1"]
        self._resolver = None
    
    async def _get_resolver(self) -> aiodns.DNSResolver:
        if self._resolver is None:
            self._resolver = aiodns.DNSResolver(nameservers=self.nameservers)
        return self._resolver
    
    async def resolve_a(self, hostname: str) -> List[str]:
        """Resolve hostname to IPv4 addresses."""
        try:
            resolver = await self._get_resolver()
            result = await resolver.query(hostname, "A")
            return [r.host for r in result]
        except aiodns.error.DNSError as e:
            logger.debug(f"DNS A query failed for {hostname}: {e}")
            return []
    
    async def resolve_aaaa(self, hostname: str) -> List[str]:
        """Resolve hostname to IPv6 addresses."""
        try:
            resolver = await self._get_resolver()
            result = await resolver.query(hostname, "AAAA")
            return [r.host for r in result]
        except aiodns.error.DNSError:
            return []
    
    async def resolve_cname(self, hostname: str) -> Optional[str]:
        """Resolve CNAME record."""
        try:
            resolver = await self._get_resolver()
            result = await resolver.query(hostname, "CNAME")
            return result.cname if result else None
        except aiodns.error.DNSError:
            return None
    
    async def resolve_mx(self, domain: str) -> List[str]:
        """Resolve MX records."""
        try:
            resolver = await self._get_resolver()
            result = await resolver.query(domain, "MX")
            return [r.host for r in result]
        except aiodns.error.DNSError:
            return []
    
    async def resolve_txt(self, domain: str) -> List[str]:
        """Resolve TXT records."""
        try:
            resolver = await self._get_resolver()
            result = await resolver.query(domain, "TXT")
            return [r.text for r in result]
        except aiodns.error.DNSError:
            return []
    
    async def reverse_lookup(self, ip: str) -> Optional[str]:
        """Perform reverse DNS lookup."""
        try:
            resolver = await self._get_resolver()
            result = await resolver.query(
                ipaddress.ip_address(ip).reverse_pointer, "PTR"
            )
            return result[0].host if result else None
        except (aiodns.error.DNSError, ValueError):
            return None


class SubdomainEnumerator:
    """Subdomain discovery through various methods."""
    
    # Common subdomain prefixes for banking/financial services
    COMMON_PREFIXES = [
        "www", "api", "app", "portal", "secure", "login", "auth",
        "banking", "online", "mobile", "m", "webmail", "mail", "smtp",
        "vpn", "remote", "gateway", "gw", "proxy", "cdn", "static",
        "assets", "img", "images", "media", "download", "docs", "help",
        "support", "admin", "console", "dashboard", "manage", "cms",
        "dev", "test", "stage", "staging", "uat", "qa", "sandbox",
        "beta", "demo", "preview", "intranet", "extranet", "partner",
        "b2b", "corporate", "enterprise", "business", "merchant",
        "payments", "pay", "transfer", "wire", "swift", "ach",
        "cards", "card", "credit", "debit", "loan", "loans", "mortgage",
        "invest", "investment", "trading", "trade", "wealth", "private",
        "fx", "forex", "treasury", "cash", "liquidity", "clearing",
        "compliance", "risk", "audit", "security", "sso", "iam", "idp",
        "oauth", "openid", "saml", "ldap", "ad", "directory",
        "ws", "webservice", "soap", "rest", "graphql", "grpc",
        "ns1", "ns2", "dns", "ntp", "time", "log", "logs", "monitor",
        "status", "health", "metrics", "grafana", "kibana", "elastic",
        "db", "database", "mysql", "postgres", "oracle", "sql",
        "redis", "cache", "memcache", "queue", "mq", "rabbit", "kafka",
        "ftp", "sftp", "file", "files", "share", "nas", "backup",
        "git", "gitlab", "github", "bitbucket", "jenkins", "ci", "cd",
        "k8s", "kubernetes", "docker", "container", "cloud", "aws", "azure", "gcp"
    ]
    
    def __init__(self, dns_resolver: DNSResolver = None):
        self.dns_resolver = dns_resolver or DNSResolver()
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=30)
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session
    
    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()
    
    async def enumerate_common_subdomains(
        self,
        domain: str,
        prefixes: List[str] = None
    ) -> AsyncIterator[str]:
        """Enumerate subdomains using common prefixes."""
        prefixes = prefixes or self.COMMON_PREFIXES
        
        async def check_subdomain(prefix: str) -> Optional[str]:
            subdomain = f"{prefix}.{domain}"
            ips = await self.dns_resolver.resolve_a(subdomain)
            if ips:
                return subdomain
            return None
        
        # Check in batches to avoid overwhelming DNS servers
        batch_size = 50
        for i in range(0, len(prefixes), batch_size):
            batch = prefixes[i:i + batch_size]
            tasks = [check_subdomain(p) for p in batch]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in results:
                if isinstance(result, str):
                    yield result
    
    async def enumerate_from_certificate_transparency(
        self,
        domain: str
    ) -> List[str]:
        """
        Query Certificate Transparency logs for subdomains.
        Uses crt.sh API.
        """
        subdomains = set()
        
        try:
            session = await self._get_session()
            url = f"https://crt.sh/?q=%.{domain}&output=json"
            
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    for entry in data:
                        name = entry.get("name_value", "")
                        # Handle wildcard and multi-line entries
                        for line in name.split("\n"):
                            line = line.strip().lstrip("*.")
                            if line.endswith(domain) and line != domain:
                                subdomains.add(line)
        except Exception as e:
            logger.warning(f"CT log query failed for {domain}: {e}")
        
        return list(subdomains)
    
    async def enumerate_from_dns_records(self, domain: str) -> List[str]:
        """Extract subdomains from DNS records (MX, TXT, etc.)."""
        subdomains = set()
        
        # Check MX records
        mx_records = await self.dns_resolver.resolve_mx(domain)
        for mx in mx_records:
            if mx.endswith(domain):
                subdomains.add(mx.rstrip("."))
        
        # Check TXT records for SPF includes
        txt_records = await self.dns_resolver.resolve_txt(domain)
        for txt in txt_records:
            # Extract domains from SPF records
            spf_match = re.findall(r'include:([^\s]+)', str(txt))
            for match in spf_match:
                if match.endswith(domain):
                    subdomains.add(match)
        
        return list(subdomains)


class PortScanner:
    """Async port scanning for service discovery."""
    
    # Common ports for banking services
    BANKING_PORTS = {
        21: "FTP",
        22: "SSH",
        25: "SMTP",
        80: "HTTP",
        110: "POP3",
        143: "IMAP",
        443: "HTTPS",
        465: "SMTPS",
        587: "SMTP-SUBMISSION",
        993: "IMAPS",
        995: "POP3S",
        1433: "MSSQL",
        1521: "ORACLE",
        3306: "MYSQL",
        3389: "RDP",
        5432: "POSTGRESQL",
        8080: "HTTP-ALT",
        8443: "HTTPS-ALT",
    }
    
    def __init__(
        self,
        timeout: float = 5.0,
        max_concurrent: int = 100
    ):
        self.timeout = timeout
        self.semaphore = asyncio.Semaphore(max_concurrent)
    
    async def check_port(
        self,
        host: str,
        port: int
    ) -> Optional[Dict]:
        """Check if a port is open."""
        async with self.semaphore:
            try:
                future = asyncio.open_connection(host, port)
                reader, writer = await asyncio.wait_for(future, timeout=self.timeout)
                writer.close()
                await writer.wait_closed()
                
                return {
                    "host": host,
                    "port": port,
                    "status": "open",
                    "protocol": self.BANKING_PORTS.get(port, "UNKNOWN")
                }
            except (asyncio.TimeoutError, ConnectionRefusedError, OSError):
                return None
    
    async def scan_host(
        self,
        host: str,
        ports: List[int] = None
    ) -> List[Dict]:
        """Scan multiple ports on a host."""
        ports = ports or list(self.BANKING_PORTS.keys())
        tasks = [self.check_port(host, port) for port in ports]
        results = await asyncio.gather(*tasks)
        return [r for r in results if r is not None]
    
    async def scan_range(
        self,
        network: str,
        ports: List[int] = None
    ) -> AsyncIterator[Dict]:
        """Scan a network range."""
        try:
            net = ipaddress.ip_network(network, strict=False)
        except ValueError as e:
            logger.error(f"Invalid network: {network} - {e}")
            return
        
        for ip in net.hosts():
            open_ports = await self.scan_host(str(ip), ports)
            for result in open_ports:
                yield result


class CloudProviderDetector:
    """Detect cloud provider from IP address."""
    
    # Known cloud provider IP ranges (simplified - in production, fetch from APIs)
    CLOUD_ASN_PATTERNS = {
        "AWS": ["AS16509", "AS14618", "AS7224"],
        "Azure": ["AS8075", "AS8068", "AS8069"],
        "GCP": ["AS15169", "AS396982"],
        "Cloudflare": ["AS13335"],
        "Akamai": ["AS16625", "AS20940"],
        "Fastly": ["AS54113"],
    }
    
    @classmethod
    async def detect_from_ip(cls, ip: str) -> Optional[str]:
        """Detect cloud provider from IP address using ASN lookup."""
        try:
            # Use Team Cymru ASN lookup
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection("whois.cymru.com", 43),
                timeout=10
            )
            
            query = f" -v {ip}\n"
            writer.write(query.encode())
            await writer.drain()
            
            response = await asyncio.wait_for(reader.read(4096), timeout=10)
            writer.close()
            await writer.wait_closed()
            
            response_text = response.decode()
            
            for provider, asns in cls.CLOUD_ASN_PATTERNS.items():
                for asn in asns:
                    if asn in response_text:
                        return provider
            
            return None
        except Exception as e:
            logger.debug(f"Cloud detection failed for {ip}: {e}")
            return None
    
    @classmethod
    def detect_from_hostname(cls, hostname: str) -> Optional[str]:
        """Detect cloud provider from hostname patterns."""
        hostname_lower = hostname.lower()
        
        patterns = {
            "AWS": [".amazonaws.com", ".aws.amazon.com", ".elasticbeanstalk.com", ".cloudfront.net"],
            "Azure": [".azure.com", ".azurewebsites.net", ".cloudapp.azure.com", ".blob.core.windows.net"],
            "GCP": [".googleapis.com", ".appspot.com", ".cloud.google.com", ".run.app"],
            "Cloudflare": [".cloudflare.com", ".workers.dev"],
            "Heroku": [".herokuapp.com"],
            "DigitalOcean": [".digitaloceanspaces.com", ".ondigitalocean.app"],
        }
        
        for provider, suffixes in patterns.items():
            for suffix in suffixes:
                if hostname_lower.endswith(suffix):
                    return provider
        
        return None


class ASNLookup:
    """ASN information lookup."""
    
    @staticmethod
    async def lookup(ip: str) -> Dict:
        """Look up ASN information for an IP address."""
        result = {
            "asn": None,
            "asn_name": None,
            "country_code": None,
        }
        
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection("whois.cymru.com", 43),
                timeout=10
            )
            
            query = f" -v {ip}\n"
            writer.write(query.encode())
            await writer.drain()
            
            response = await asyncio.wait_for(reader.read(4096), timeout=10)
            writer.close()
            await writer.wait_closed()
            
            lines = response.decode().strip().split("\n")
            if len(lines) >= 2:
                # Skip header, parse data line
                parts = [p.strip() for p in lines[-1].split("|")]
                if len(parts) >= 3:
                    result["asn"] = f"AS{parts[0]}" if parts[0] else None
                    result["country_code"] = parts[1] if parts[1] else None
                    result["asn_name"] = parts[-1] if len(parts) > 3 else None
        
        except Exception as e:
            logger.debug(f"ASN lookup failed for {ip}: {e}")
        
        return result


class AssetDiscoveryEngine:
    """
    Main asset discovery engine that orchestrates all discovery methods.
    """
    
    def __init__(self):
        self.dns_resolver = DNSResolver()
        self.subdomain_enumerator = SubdomainEnumerator(self.dns_resolver)
        self.port_scanner = PortScanner(
            timeout=settings.SCAN_TIMEOUT_SECONDS,
            max_concurrent=settings.SCAN_MAX_CONCURRENT
        )
    
    async def close(self):
        """Clean up resources."""
        await self.subdomain_enumerator.close()
    
    async def discover_domain(
        self,
        domain: str,
        include_subdomains: bool = True,
        ports: List[int] = None
    ) -> List[DiscoveredAsset]:
        """
        Discover all assets for a domain.
        """
        discovered: List[DiscoveredAsset] = []
        processed_hosts: Set[str] = set()
        
        logger.info(f"Starting discovery for domain: {domain}")
        
        # Collect all hostnames to scan
        hostnames = {domain}
        
        if include_subdomains:
            # Enumerate subdomains using multiple methods
            logger.info(f"Enumerating subdomains for {domain}")
            
            # Common prefixes
            async for subdomain in self.subdomain_enumerator.enumerate_common_subdomains(domain):
                hostnames.add(subdomain)
            
            # Certificate transparency
            ct_subdomains = await self.subdomain_enumerator.enumerate_from_certificate_transparency(domain)
            hostnames.update(ct_subdomains)
            
            # DNS records
            dns_subdomains = await self.subdomain_enumerator.enumerate_from_dns_records(domain)
            hostnames.update(dns_subdomains)
        
        logger.info(f"Found {len(hostnames)} unique hostnames for {domain}")
        
        # Discover assets for each hostname
        for hostname in hostnames:
            if hostname in processed_hosts:
                continue
            processed_hosts.add(hostname)
            
            # Resolve IP addresses
            ips = await self.dns_resolver.resolve_a(hostname)
            if not ips:
                continue
            
            ip = ips[0]  # Use first IP
            
            # Scan ports
            ports = ports or [443, 8443, 80, 8080]
            open_ports = await self.port_scanner.scan_host(ip, ports)
            
            for port_info in open_ports:
                # Get additional information
                asn_info = await ASNLookup.lookup(ip)
                cloud_provider = (
                    CloudProviderDetector.detect_from_hostname(hostname) or
                    await CloudProviderDetector.detect_from_ip(ip)
                )
                
                asset = DiscoveredAsset(
                    hostname=hostname,
                    ip_address=ip,
                    port=port_info["port"],
                    protocol=port_info["protocol"],
                    discovery_source="domain_enumeration",
                    asn=asn_info.get("asn"),
                    asn_name=asn_info.get("asn_name"),
                    country_code=asn_info.get("country_code"),
                    cloud_provider=cloud_provider,
                    is_accessible=True,
                )
                discovered.append(asset)
        
        logger.info(f"Discovery complete for {domain}: {len(discovered)} assets found")
        return discovered
    
    async def discover_ip_range(
        self,
        network: str,
        ports: List[int] = None
    ) -> List[DiscoveredAsset]:
        """
        Discover assets in an IP range.
        """
        discovered: List[DiscoveredAsset] = []
        
        logger.info(f"Starting discovery for network: {network}")
        
        async for port_info in self.port_scanner.scan_range(network, ports):
            ip = port_info["host"]
            
            # Reverse DNS lookup
            hostname = await self.dns_resolver.reverse_lookup(ip)
            
            # Get ASN info
            asn_info = await ASNLookup.lookup(ip)
            cloud_provider = await CloudProviderDetector.detect_from_ip(ip)
            
            asset = DiscoveredAsset(
                hostname=hostname or ip,
                ip_address=ip,
                port=port_info["port"],
                protocol=port_info["protocol"],
                discovery_source="ip_range_scan",
                asn=asn_info.get("asn"),
                asn_name=asn_info.get("asn_name"),
                country_code=asn_info.get("country_code"),
                cloud_provider=cloud_provider,
                is_accessible=True,
            )
            discovered.append(asset)
        
        logger.info(f"IP range discovery complete: {len(discovered)} assets found")
        return discovered
    
    async def discover_asn(
        self,
        asn: str,
        ports: List[int] = None
    ) -> List[DiscoveredAsset]:
        """
        Discover assets by ASN.
        This requires external data sources for ASN prefix lists.
        """
        # Note: In production, this would query RIR databases or BGP data
        # to get IP prefixes for the ASN, then scan those ranges
        logger.info(f"ASN-based discovery for {asn}")
        
        # Placeholder for ASN prefix lookup
        # In production, use RIPE, ARIN, or BGP data sources
        raise NotImplementedError(
            "ASN-based discovery requires integration with RIR databases. "
            "Configure RIPE_API_KEY or use BGP data sources."
        )
