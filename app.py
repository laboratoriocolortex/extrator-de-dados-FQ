import React, { useState, useEffect, useRef } from 'react';
import { Upload, FileText, Download, Trash2, History, Loader2, CheckCircle, AlertCircle } from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';

interface Extraction {
  id: number;
  created_at: string;
  filename: string;
  product: string;
  lote: string;
  ini_pig: string;
  fim_pig: string;
  ini_fq: string;
  fim_fq: string;
  visc: string;
  ph: string;
  dens: string;
  status: string;
}

export default function App() {
  const [extractions, setExtractions] = useState<Extraction[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    fetchHistory();
  }, []);

  const fetchHistory = async () => {
    try {
      const res = await fetch('/api/history');
      const data = await res.json();
      setExtractions(data);
    } catch (err) {
      console.error('Failed to load history', err);
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;

    setLoading(true);
    setError(null);

    // Process files sequentially to maintain order and not overwhelm
    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      try {
        const base64 = await convertToBase64(file);
        const res = await fetch('/api/extract', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ image: base64, filename: file.name }),
        });

        if (!res.ok) throw new Error(`Failed to process ${file.name}`);
        
        const newData = await res.json();
        setExtractions(prev => [newData, ...prev]);
      } catch (err) {
        setError(`Erro ao processar ${file.name}. Tente novamente.`);
      }
    }
    setLoading(false);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const convertToBase64 = (file: File): Promise<string> => {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.readAsDataURL(file);
      reader.onload = () => resolve(reader.result as string);
      reader.onerror = error => reject(error);
    });
  };

  const handleDelete = async (id: number) => {
    try {
      await fetch(`/api/history/${id}`, { method: 'DELETE' });
      setExtractions(prev => prev.filter(item => item.id !== id));
    } catch (err) {
      console.error('Failed to delete', err);
    }
  };

  const downloadCSV = () => {
    if (extractions.length === 0) return;

    const headers = [
      "Data", "Arquivo", "Produto", "Lote", 
      "Ini Pigmentação", "Fim Pigmentação", 
      "Ini Análise FQ", "Fim Análise FQ", 
      "Viscosidade", "pH", "Densidade", "Status"
    ];

    const csvContent = [
      headers.join(';'),
      ...extractions.map(row => [
        new Date(row.created_at).toLocaleString('pt-BR'),
        row.filename,
        row.product,
        row.lote,
        row.ini_pig,
        row.fim_pig,
        row.ini_fq,
        row.fim_fq,
        row.visc,
        row.ph,
        row.dens,
        row.status
      ].join(';'))
    ].join('\n');

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.setAttribute('href', url);
    link.setAttribute('download', `extracao_tintas_${new Date().toISOString().split('T')[0]}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 font-sans">
      {/* Header */}
      <header className="bg-white border-b border-slate-200 sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="bg-indigo-600 p-2 rounded-lg">
              <FileText className="w-6 h-6 text-white" />
            </div>
            <h1 className="text-xl font-semibold text-slate-900">Extrator de Diários de Produção</h1>
          </div>
          <div className="flex items-center gap-4">
            <button 
              onClick={downloadCSV}
              disabled={extractions.length === 0}
              className="flex items-center gap-2 px-4 py-2 bg-white border border-slate-300 rounded-lg text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              <Download className="w-4 h-4" />
              Baixar CSV
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        
        {/* Upload Section */}
        <section className="mb-8">
          <div 
            onClick={() => fileInputRef.current?.click()}
            className={`
              relative border-2 border-dashed rounded-2xl p-12 text-center cursor-pointer transition-all
              ${loading ? 'border-indigo-300 bg-indigo-50' : 'border-slate-300 hover:border-indigo-500 hover:bg-slate-50 bg-white'}
            `}
          >
            <input 
              type="file" 
              ref={fileInputRef} 
              onChange={handleFileUpload} 
              className="hidden" 
              multiple 
              accept="image/*"
            />
            
            <div className="flex flex-col items-center gap-4">
              {loading ? (
                <>
                  <Loader2 className="w-12 h-12 text-indigo-600 animate-spin" />
                  <p className="text-lg font-medium text-indigo-700">Processando imagens com IA...</p>
                </>
              ) : (
                <>
                  <div className="w-16 h-16 bg-indigo-100 text-indigo-600 rounded-full flex items-center justify-center mb-2">
                    <Upload className="w-8 h-8" />
                  </div>
                  <div>
                    <p className="text-lg font-medium text-slate-900">Clique para fazer upload ou arraste as fotos</p>
                    <p className="text-slate-500 mt-1">Suporta múltiplas imagens (JPG, PNG)</p>
                  </div>
                </>
              )}
            </div>
          </div>
          {error && (
            <div className="mt-4 p-4 bg-red-50 text-red-700 rounded-lg flex items-center gap-2">
              <AlertCircle className="w-5 h-5" />
              {error}
            </div>
          )}
        </section>

        {/* Data Table */}
        <section className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
          <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between bg-slate-50">
            <div className="flex items-center gap-2">
              <History className="w-5 h-5 text-slate-500" />
              <h2 className="font-semibold text-slate-900">Histórico de Extrações</h2>
            </div>
            <span className="text-sm text-slate-500">{extractions.length} registros encontrados</span>
          </div>
          
          <div className="overflow-x-auto">
            <table className="w-full text-sm text-left">
              <thead className="bg-slate-50 text-slate-500 font-medium border-b border-slate-200">
                <tr>
                  <th className="px-6 py-3 whitespace-nowrap">Data</th>
                  <th className="px-6 py-3 whitespace-nowrap">Produto</th>
                  <th className="px-6 py-3 whitespace-nowrap">Lote</th>
                  <th className="px-6 py-3 whitespace-nowrap text-center" colSpan={2}>Pigmentação</th>
                  <th className="px-6 py-3 whitespace-nowrap text-center" colSpan={2}>Análise FQ</th>
                  <th className="px-6 py-3 whitespace-nowrap">Visc</th>
                  <th className="px-6 py-3 whitespace-nowrap">pH</th>
                  <th className="px-6 py-3 whitespace-nowrap">Dens</th>
                  <th className="px-6 py-3 whitespace-nowrap">Ações</th>
                </tr>
                <tr className="border-b border-slate-200 text-xs uppercase tracking-wider">
                  <th className="px-6 py-1"></th>
                  <th className="px-6 py-1"></th>
                  <th className="px-6 py-1"></th>
                  <th className="px-6 py-1 text-center bg-slate-100">Início</th>
                  <th className="px-6 py-1 text-center bg-slate-100">Fim</th>
                  <th className="px-6 py-1 text-center bg-slate-100">Início</th>
                  <th className="px-6 py-1 text-center bg-slate-100">Fim</th>
                  <th className="px-6 py-1"></th>
                  <th className="px-6 py-1"></th>
                  <th className="px-6 py-1"></th>
                  <th className="px-6 py-1"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200">
                <AnimatePresence>
                  {extractions.map((row) => (
                    <motion.tr 
                      key={row.id}
                      initial={{ opacity: 0, y: -10 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, height: 0 }}
                      className="hover:bg-slate-50 transition-colors"
                    >
                      <td className="px-6 py-4 whitespace-nowrap text-slate-500">
                        {new Date(row.created_at).toLocaleDateString('pt-BR')}
                        <div className="text-xs text-slate-400">{new Date(row.created_at).toLocaleTimeString('pt-BR', {hour: '2-digit', minute:'2-digit'})}</div>
                      </td>
                      <td className="px-6 py-4 font-medium text-slate-900">{row.product}</td>
                      <td className="px-6 py-4 font-mono text-slate-600">{row.lote}</td>
                      <td className="px-6 py-4 text-center text-slate-600">{row.ini_pig}</td>
                      <td className="px-6 py-4 text-center text-slate-600">{row.fim_pig}</td>
                      <td className="px-6 py-4 text-center text-slate-600">{row.ini_fq}</td>
                      <td className="px-6 py-4 text-center text-slate-600">{row.fim_fq}</td>
                      <td className="px-6 py-4 text-slate-600">{row.visc}</td>
                      <td className="px-6 py-4 text-slate-600">{row.ph}</td>
                      <td className="px-6 py-4 text-slate-600">{row.dens}</td>
                      <td className="px-6 py-4">
                        <button 
                          onClick={() => handleDelete(row.id)}
                          className="p-2 text-slate-400 hover:text-red-600 hover:bg-red-50 rounded-full transition-colors"
                          title="Excluir registro"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </td>
                    </motion.tr>
                  ))}
                </AnimatePresence>
                {extractions.length === 0 && (
                  <tr>
                    <td colSpan={11} className="px-6 py-12 text-center text-slate-500">
                      Nenhum dado extraído ainda. Faça upload de uma imagem para começar.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </section>
      </main>
    </div>
  );
}
