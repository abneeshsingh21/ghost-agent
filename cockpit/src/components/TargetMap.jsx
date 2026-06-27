import React, { useState, useEffect } from 'react';
import { Map, Server, Wifi, Smartphone, Monitor, Globe } from 'lucide-react';

/**
 * TargetMap — Live network topology built from parsed tool output.
 * Listens to 'intelligence_update' socket events (from _auto_parse_and_update).
 * Renders discovered hosts with ports, OS, and risk indicators.
 */
const TargetMap = ({ socket }) => {
  const [hosts, setHosts] = useState({});

  const riskColor = (ports = []) => {
    const high = [21, 22, 23, 25, 80, 443, 445, 3389, 5555, 8080];
    const hasHigh = ports.some(p => high.includes(p));
    if (ports.length === 0) return '#64748b';
    if (ports.length > 8 || hasHigh) return '#f43f5e';
    if (ports.length > 4) return '#fbbf24';
    return '#34d399';
  };

  const osIcon = (os = '') => {
    const lower = os.toLowerCase();
    if (lower.includes('android') || lower.includes('mobile')) return <Smartphone size={12} />;
    if (lower.includes('windows')) return <Monitor size={12} />;
    if (lower.includes('linux') || lower.includes('ubuntu') || lower.includes('debian')) return <Server size={12} />;
    if (lower.includes('router') || lower.includes('cisco') || lower.includes('mikrotik')) return <Wifi size={12} />;
    return <Globe size={12} />;
  };

  useEffect(() => {
    if (!socket) return;

    // Populate from initial status
    fetch('http://localhost:5000/api/status')
      .then(r => r.json())
      .then(data => {
        const sessionHosts = data?.memory?.session?.discovered_hosts || [];
        sessionHosts.forEach(h => {
          if (h.ip) {
            setHosts(prev => ({ ...prev, [h.ip]: h }));
          }
        });
      })
      .catch(() => {});

    // Live updates from parser
    socket.on('intelligence_update', (data) => {
      const incomingHosts = data.hosts || [];
      setHosts(prev => {
        const updated = { ...prev };
        incomingHosts.forEach(h => {
          if (!h.ip) return;
          if (updated[h.ip]) {
            // Merge ports
            const existingPorts = new Set(updated[h.ip].ports || []);
            (h.ports || []).forEach(p => existingPorts.add(p));
            updated[h.ip] = {
              ...updated[h.ip],
              ports: [...existingPorts].sort((a, b) => a - b),
              os: h.os || updated[h.ip].os,
              services: [...(updated[h.ip].services || []), ...(h.services || [])],
              status: h.status || updated[h.ip].status,
            };
          } else {
            updated[h.ip] = h;
          }
        });
        return updated;
      });
    });

    socket.on('c2_session_callback', (data) => {
      const info = data.info || {};
      const peer = info.tunnel_peer || '';
      const ip = peer.split(':')[0];
      if (ip) {
        setHosts(prev => ({
          ...prev,
          [ip]: {
            ...prev[ip],
            ip,
            os: info.os || prev[ip]?.os || '',
            status: 'compromised',
            c2_session: data.session_id,
          }
        }));
      }
    });

    return () => {
      socket.off('intelligence_update');
      socket.off('c2_session_callback');
    };
  }, [socket]);

  const hostList = Object.values(hosts);

  return (
    <div className="glass-panel" style={{ flex: 1, minHeight: 0 }}>
      <div className="panel-header" style={{ color: '#34d399' }}>
        <Map size={16} /> Target Map
        <span style={{
          marginLeft: 'auto', fontSize: '0.7rem', fontWeight: 'normal',
          color: 'var(--text-muted)'
        }}>
          {hostList.length} host{hostList.length !== 1 ? 's' : ''} known
        </span>
      </div>
      <div className="panel-content" style={{ padding: '10px', overflowY: 'auto' }}>

        {hostList.length === 0 ? (
          <div style={{
            display: 'flex', flexDirection: 'column', alignItems: 'center',
            justifyContent: 'center', height: '100%', color: 'var(--text-muted)',
            gap: '10px',
          }}>
            <Map size={32} style={{ opacity: 0.2 }} />
            <span style={{ fontSize: '0.8rem' }}>No hosts discovered yet.</span>
            <span style={{ fontSize: '0.72rem', opacity: 0.7 }}>Run nmap/arp-scan to populate the target map.</span>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {hostList.map((host) => {
              const color = riskColor(host.ports);
              const isCompromised = host.status === 'compromised';
              return (
                <div key={host.ip} style={{
                  background: isCompromised
                    ? 'rgba(244, 63, 94, 0.08)'
                    : 'rgba(0,0,0,0.3)',
                  border: `1px solid ${isCompromised ? '#f43f5e44' : color + '33'}`,
                  borderRadius: '8px',
                  padding: '8px 10px',
                  transition: 'all 0.2s ease',
                }}>
                  {/* Header row */}
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                    {/* Risk dot */}
                    <div style={{
                      width: '8px', height: '8px', borderRadius: '50%',
                      background: isCompromised ? '#f43f5e' : color,
                      boxShadow: `0 0 6px ${isCompromised ? '#f43f5e' : color}`,
                      flexShrink: 0,
                    }} />
                    <span style={{ fontWeight: '600', color: '#f8fafc', fontSize: '0.88rem', fontFamily: 'monospace' }}>
                      {host.ip}
                    </span>
                    {host.hostname && (
                      <span style={{ color: 'var(--text-muted)', fontSize: '0.72rem' }}>
                        ({host.hostname})
                      </span>
                    )}
                    {isCompromised && (
                      <span style={{
                        marginLeft: 'auto', fontSize: '0.65rem', fontWeight: 'bold',
                        color: '#f43f5e', background: 'rgba(244,63,94,0.15)',
                        padding: '1px 6px', borderRadius: '20px', border: '1px solid #f43f5e44',
                      }}>
                        OWNED
                      </span>
                    )}
                    {host.c2_session && (
                      <span style={{
                        marginLeft: isCompromised ? '4px' : 'auto',
                        fontSize: '0.65rem', color: '#f43f5e',
                      }}>
                        SID:{host.c2_session}
                      </span>
                    )}
                  </div>

                  {/* OS + vendor */}
                  {(host.os || host.vendor) && (
                    <div style={{
                      display: 'flex', alignItems: 'center', gap: '4px',
                      color: 'var(--text-muted)', fontSize: '0.72rem', marginBottom: '4px',
                    }}>
                      <span style={{ color: '#94a3b8' }}>{osIcon(host.os)}</span>
                      {host.os || host.vendor}
                    </div>
                  )}

                  {/* Ports */}
                  {host.ports && host.ports.length > 0 && (
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
                      {host.ports.slice(0, 12).map(port => (
                        <span key={port} style={{
                          fontSize: '0.68rem', padding: '1px 5px',
                          background: 'rgba(255,255,255,0.06)',
                          border: '1px solid rgba(255,255,255,0.1)',
                          borderRadius: '3px', fontFamily: 'monospace',
                          color: [22, 80, 443, 3389, 5555].includes(port) ? '#fbbf24' : 'var(--text-muted)',
                        }}>
                          {port}
                        </span>
                      ))}
                      {host.ports.length > 12 && (
                        <span style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>
                          +{host.ports.length - 12} more
                        </span>
                      )}
                    </div>
                  )}

                  {/* Services preview */}
                  {host.services && host.services.length > 0 && (
                    <div style={{
                      marginTop: '4px', fontSize: '0.68rem',
                      color: 'var(--text-muted)', overflow: 'hidden',
                      textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                    }}>
                      {host.services.slice(0, 4).map(s =>
                        `${s.service}${s.version ? ' ' + s.version.split(' ')[0] : ''}`
                      ).join(' · ')}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};

export default TargetMap;
