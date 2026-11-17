// 함께반(cotutor) QrCode.tsx 패턴: qrcode 패키지로 data URL을 만든다.
import { useEffect, useState } from 'react';
import QRCode from 'qrcode';

export function QrCode({ value, size, label }: { value: string; size: number; label: string }) {
  const [src, setSrc] = useState('');
  const [error, setError] = useState('');
  useEffect(() => {
    let active = true;
    QRCode.toDataURL(value, { width: 480, margin: 1, errorCorrectionLevel: 'M', color: { dark: '#2B1A22', light: '#FFFFFF' } })
      .then((url) => active && (setSrc(url), setError('')))
      .catch(() => active && setError('QR 그림을 만들지 못했어요.'));
    return () => {
      active = false;
    };
  }, [value]);
  if (error) return <p role="alert" className="err">{error}</p>;
  return src ? <img src={src} width={size} height={size} alt={label} /> : <div style={{ width: size, height: size }} aria-hidden />;
}
