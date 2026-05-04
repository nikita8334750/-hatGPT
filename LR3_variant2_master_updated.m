% LR3 variant 2. Spectral processing
clear; clc; close all;
files={'V_02.mat','v_2.mat','V_2.mat','v_02.mat'}; matFile='';
for i=1:numel(files), if isfile(files{i}), matFile=files{i}; break; end, end
if isempty(matFile)
    [fn,fp]=uigetfile('*.mat','Select V_02.mat');
    if isequal(fn,0), error('File not selected'); end
    matFile=fullfile(fp,fn);
end
load(matFile);
if ~exist('Fs','var')||~exist('s','var')||~exist('t','var'), error('Need Fs, s, t'); end
s=s(:); t=t(:); N=numel(s); if numel(t)~=N, error('s and t lengths differ'); end
outDir='LR3_variant2_output'; figDir=fullfile(outDir,'figures');
if ~exist(outDir,'dir'), mkdir(outDir); end; if ~exist(figDir,'dir'), mkdir(figDir); end
S=fft(s); A2=abs(S)/N; Nh=floor(N/2)+1; A1=A2(1:Nh); if N>2, A1(2:end-1)=2*A1(2:end-1); end
f=(0:Nh-1)'*Fs/N; As=A1; As(1)=0; [Amax,k]=max(As); f0=f(k); thr=0.5*Amax;
figure; plot(t,s); grid on; xlabel('t, s'); ylabel('s(t)'); title('Source signal'); saveas(gcf,fullfile(figDir,'01_ishodny_signal.png'));
figure; plot(f,A1); grid on; xlabel('f, Hz'); ylabel('|S(f)|'); title('Amplitude spectrum'); xlim([0 Fs/2]); saveas(gcf,fullfile(figDir,'02_amplitudny_spektr.png'));
idx=f>=max(0,f0-10)&f<=min(Fs/2,f0+10); figure; plot(f(idx),A1(idx)); grid on; title(sprintf('Peak near %.2f Hz',f0)); xlabel('f, Hz'); saveas(gcf,fullfile(figDir,'03_fragment_spektra_okolo_pika.png'));
Ath=A1; Ath(Ath<thr)=0; figure; stem(f,Ath,'filled'); grid on; title('Thresholded spectrum'); xlabel('f, Hz'); xlim([0 Fs/2]); saveas(gcf,fullfile(figDir,'04_porogovaya_obrabotka.png'));
m=k-1; if m==0, knew=1; else, knew=N-m+1; end; St=zeros(size(S)); St(k)=S(k); if knew~=k, St(knew)=S(knew); end
srec=real(ifft(St)); figure; plot(t,srec); grid on; xlabel('t, s'); title('Restored harmonic'); saveas(gcf,fullfile(figDir,'05_vosstanovlenny_signal.png'));
figure; plot(t,s); hold on; plot(t,srec); grid on; legend('source','restored'); title('Comparison'); saveas(gcf,fullfile(figDir,'06_sravnenie_signalov.png'));
fid=fopen(fullfile(outDir,'LR3_variant2_report_values.txt'),'w'); fprintf(fid,'Fs=%.6f\nN=%d\ndf=%.6f\nf0=%.6f\nAmax=%.6f\nthreshold=%.6f\n',Fs,N,Fs/N,f0,Amax,thr); fclose(fid);
signal_for_simulink=[t s]; signal_ts=timeseries(s,t); save(fullfile(outDir,'LR3_variant2_results.mat'),'Fs','s','t','f','A1','srec','f0','thr','signal_for_simulink','signal_ts');
fprintf('Done. f0=%.6f Hz. Figures: %s\n',f0,figDir);
