import React, { useState, useEffect } from 'react';
import { Plus, Thermometer, Target, TrendingUp, Save, Calculator, Settings, Wrench, Zap, BarChart3, Users, Download, Bell, Flame, Activity } from 'lucide-react';

const KilnOffsetTracker = () => {
  const [activeTab, setActiveTab] = useState('firing');
  const [firings, setFirings] = useState([]);
  const [hardware, setHardware] = useState({
    elements: { installed: '', firingCount: 0, maxLife: 300 },
    thermocouples: { installed: '', firingCount: 0, maxLife: 1000 },
    relays: { installed: '', firingCount: 0, maxLife: 500 }
  });
  
  // Multi-zone offsets
  const [zoneOffsets, setZoneOffsets] = useState({
    top: 18,
    middle: 18,
    bottom: 18
  });
  
  // Current firing form
  const [currentOffset, setCurrentOffset] = useState(18);
  const [targetCone, setTargetCone] = useState(6);
  const [actualResult, setActualResult] = useState('');
  const [firingType, setFiringType] = useState('glaze');
  const [clayBody, setClayBody] = useState('');
  const [glazeType, setGlazeType] = useState('');
  const [loadDensity, setLoadDensity] = useState('full');
  const [notes, setNotes] = useState('');
  const [zoneResults, setZoneResults] = useState({
    top: '',
    middle: '',
    bottom: ''
  });

  // Firing programs
  const [programs, setPrograms] = useState([]);
  const [newProgram, setNewProgram] = useState({
    name: '',
    type: 'glaze',
    targetTemp: 2165,
    rampRate: 150,
    holdTime: 10,
    clayBody: '',
    notes: ''
  });

  // Cone temperature reference
  const coneTemps = {
    '04': 1830, '03': 1850, '02': 1870, '01': 1890, '1': 1910,
    '2': 1920, '3': 1930, '4': 1945, '5': 1975, '6': 1995,
    '7': 2015, '8': 2035, '9': 2055, '10': 2075
  };

  const clayBodies = [
    'Cone 6 Stoneware', 'Porcelain', 'Buff Stoneware', 'White Stoneware', 
    'Speckled Stoneware', 'Dark Stoneware', 'Earthenware', 'Custom Mix'
  ];

  // Load data from localStorage
  useEffect(() => {
    const savedFirings = localStorage.getItem('kilnFirings');
    const savedOffsets = localStorage.getItem('zoneOffsets');
    const savedHardware = localStorage.getItem('kilnHardware');
    const savedPrograms = localStorage.getItem('firingPrograms');
    
    if (savedFirings) setFirings(JSON.parse(savedFirings));
    if (savedOffsets) setZoneOffsets(JSON.parse(savedOffsets));
    if (savedHardware) setHardware(JSON.parse(savedHardware));
    if (savedPrograms) setPrograms(JSON.parse(savedPrograms));
  }, []);

  // Save to localStorage
  useEffect(() => {
    localStorage.setItem('kilnFirings', JSON.stringify(firings));
    localStorage.setItem('zoneOffsets', JSON.stringify(zoneOffsets));
    localStorage.setItem('kilnHardware', JSON.stringify(hardware));
    localStorage.setItem('firingPrograms', JSON.stringify(programs));
  }, [firings, zoneOffsets, hardware, programs]);

  const addFiring = () => {
    if (!actualResult.trim()) return;

    const newFiring = {
      id: Date.now(),
      date: new Date().toLocaleDateString(),
      time: new Date().toLocaleTimeString(),
      zoneOffsets: { ...zoneOffsets },
      targetCone,
      actualResult: actualResult.trim(),
      zoneResults: { ...zoneResults },
      firingType,
      clayBody,
      glazeType,
      loadDensity,
      notes: notes.trim(),
      timestamp: Date.now()
    };

    setFirings(prev => [newFiring, ...prev]);
    
    // Update hardware firing counts
    setHardware(prev => ({
      ...prev,
      elements: { ...prev.elements, firingCount: prev.elements.firingCount + 1 },
      thermocouples: { ...prev.thermocouples, firingCount: prev.thermocouples.firingCount + 1 },
      relays: { ...prev.relays, firingCount: prev.relays.firingCount + 1 }
    }));
    
    // Reset form
    setActualResult('');
    setZoneResults({ top: '', middle: '', bottom: '' });
    setNotes('');
    setGlazeType('');
  };

  const addProgram = () => {
    if (!newProgram.name.trim()) return;

    const program = {
      id: Date.now(),
      ...newProgram,
      created: new Date().toLocaleDateString()
    };

    setPrograms(prev => [program, ...prev]);
    setNewProgram({
      name: '',
      type: 'glaze',
      targetTemp: 2165,
      rampRate: 150,
      holdTime: 10,
      clayBody: '',
      notes: ''
    });
  };

  const calculateSuggestedOffsets = () => {
    if (firings.length === 0) return null;

    const recentFirings = firings.slice(0, 5);
    const suggestions = { top: 0, middle: 0, bottom: 0 };
    
    ['top', 'middle', 'bottom'].forEach(zone => {
      let totalAdjustment = 0;
      let validFirings = 0;

      recentFirings.forEach(firing => {
        const result = firing.zoneResults[zone]?.toLowerCase() || firing.actualResult.toLowerCase();
        const target = firing.targetCone;

        if (result.includes('cone')) {
          if (result.includes('hot') || result.includes('soft')) {
            totalAdjustment += 12;
            validFirings++;
          } else if (result.includes('perfect') || result.includes('good')) {
            totalAdjustment += 0;
            validFirings++;
          } else {
            const coneMatch = result.match(/cone\s*(\d+)/);
            if (coneMatch) {
              const actualCone = parseInt(coneMatch[1]);
              if (actualCone > target) {
                totalAdjustment += (actualCone - target) * 18;
                validFirings++;
              } else if (actualCone < target) {
                totalAdjustment -= (target - actualCone) * 18;
                validFirings++;
              }
            }
          }
        }
      });

      if (validFirings > 0) {
        const adjustment = Math.round(totalAdjustment / validFirings);
        suggestions[zone] = Math.max(0, Math.min(100, zoneOffsets[zone] + adjustment));
      } else {
        suggestions[zone] = zoneOffsets[zone];
      }
    });

    return suggestions;
  };

  const getHealthStatus = (component) => {
    const usage = (component.firingCount / component.maxLife) * 100;
    if (usage < 60) return { color: 'text-emerald-600', status: 'Excellent', bg: 'bg-gradient-to-br from-emerald-50 to-green-100', ring: 'ring-emerald-200' };
    if (usage < 85) return { color: 'text-amber-600', status: 'Monitor', bg: 'bg-gradient-to-br from-amber-50 to-yellow-100', ring: 'ring-amber-200' };
    return { color: 'text-red-600', status: 'Replace Soon', bg: 'bg-gradient-to-br from-red-50 to-rose-100', ring: 'ring-red-200' };
  };

  const exportData = () => {
    const data = {
      firings,
      zoneOffsets,
      hardware,
      programs,
      exported: new Date().toISOString()
    };
    
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `kiln-data-${new Date().toISOString().split('T')[0]}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const suggestedOffsets = calculateSuggestedOffsets();

  const tabs = [
    { id: 'firing', label: 'Firing Log', icon: Flame, color: 'from-orange-500 to-red-500' },
    { id: 'zones', label: 'Zone Control', icon: Target, color: 'from-blue-500 to-cyan-500' },
    { id: 'programs', label: 'Programs', icon: Settings, color: 'from-purple-500 to-indigo-500' },
    { id: 'hardware', label: 'Maintenance', icon: Wrench, color: 'from-green-500 to-emerald-500' },
    { id: 'analytics', label: 'Analytics', icon: BarChart3, color: 'from-pink-500 to-rose-500' },
    { id: 'help', label: 'Help', icon: Users, color: 'from-teal-500 to-cyan-500' },
    { id: 'about', label: 'About', icon: Thermometer, color: 'from-slate-500 to-gray-500' }
  ];

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-100">
      <div className="max-w-7xl mx-auto p-4 md:p-6">
        <div className="bg-white/80 backdrop-blur-sm rounded-3xl shadow-2xl border border-white/20 overflow-hidden">
          {/* Header */}
          <div className="relative p-6 md:p-8 bg-gradient-to-r from-orange-500 via-red-500 to-pink-500">
            <div className="absolute inset-0 bg-black/10"></div>
            <div className="relative flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
              <div className="flex items-center gap-4">
                <div className="p-3 bg-white/20 rounded-2xl backdrop-blur-sm">
                  <Flame className="w-8 h-8 text-white" />
                </div>
                <div>
                  <h1 className="text-2xl md:text-4xl font-bold text-white drop-shadow-lg break-words">KilnMaster Pro</h1>
                  <p className="text-white/80 text-base md:text-lg break-words">Advanced Kiln Management & Analytics</p>
                </div>
              </div>
              <button
                onClick={exportData}
                className="flex items-center gap-2 px-4 md:px-6 py-2 md:py-3 bg-white/20 backdrop-blur-sm text-white rounded-xl hover:bg-white/30 transition-all duration-200 shadow-lg text-sm md:text-base whitespace-nowrap"
              >
                <Download className="w-4 h-4" />
                Export Data
              </button>
            </div>
          </div>

          {/* Tabs */}
          <div className="flex bg-gradient-to-r from-gray-50 to-slate-100 border-b overflow-x-auto">
            {tabs.map(tab => {
              const Icon = tab.icon;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`relative flex items-center gap-3 px-6 py-4 font-medium transition-all duration-300 whitespace-nowrap min-w-fit ${
                    activeTab === tab.id
                      ? 'text-white shadow-lg transform -translate-y-1'
                      : 'text-gray-600 hover:text-gray-800 hover:bg-white/50'
                  }`}
                  style={activeTab === tab.id ? {
                    background: `linear-gradient(135deg, ${tab.color.split(' ')[1]}, ${tab.color.split(' ')[3]})`
                  } : {}}
                >
                  <Icon className="w-5 h-5 flex-shrink-0" />
                  <span className="text-sm md:text-base">{tab.label}</span>
                  {activeTab === tab.id && (
                    <div className="absolute bottom-0 left-1/2 transform -translate-x-1/2 w-2 h-2 bg-white rounded-full"></div>
                  )}
                </button>
              );
            })}
          </div>

          {/* Tab Content */}
          <div className="p-4 md:p-6 lg:p-8">
            {activeTab === 'firing' && (
              <div className="space-y-8">
                {/* Dashboard Cards */}
                <div className="grid md:grid-cols-4 gap-6">
                  <div className="bg-gradient-to-br from-orange-500 to-red-500 rounded-2xl p-6 text-white shadow-xl">
                    <div className="flex items-center justify-between mb-4">
                      <div className="p-2 bg-white/20 rounded-lg">
                        <Target className="w-6 h-6" />
                      </div>
                      <Activity className="w-8 h-8 opacity-50" />
                    </div>
                    <h3 className="text-white/80 text-sm font-medium mb-3">Zone Offsets</h3>
                    <div className="space-y-2">
                      <div className="flex justify-between text-sm">
                        <span className="min-w-0">Top</span>
                        <span className="font-mono font-bold flex-shrink-0">{zoneOffsets.top}°F</span>
                      </div>
                      <div className="flex justify-between text-sm">
                        <span className="min-w-0">Middle</span>
                        <span className="font-mono font-bold flex-shrink-0">{zoneOffsets.middle}°F</span>
                      </div>
                      <div className="flex justify-between text-sm">
                        <span className="min-w-0">Bottom</span>
                        <span className="font-mono font-bold flex-shrink-0">{zoneOffsets.bottom}°F</span>
                      </div>
                    </div>
                  </div>

                  <div className="bg-gradient-to-br from-blue-500 to-cyan-500 rounded-2xl p-6 text-white shadow-xl">
                    <div className="flex items-center justify-between mb-4">
                      <div className="p-2 bg-white/20 rounded-lg">
                        <TrendingUp className="w-6 h-6" />
                      </div>
                      <div className="text-3xl font-bold">{firings.length}</div>
                    </div>
                    <h3 className="text-white/80 text-sm font-medium">Total Firings</h3>
                    <p className="text-white/60 text-xs mt-2">Lifetime records</p>
                  </div>

                  <div className={`rounded-2xl p-6 text-white shadow-xl ${getHealthStatus(hardware.elements).bg.replace('bg-', 'bg-')}`}>
                    <div className="flex items-center justify-between mb-4">
                      <div className="p-2 bg-white/20 rounded-lg">
                        <Zap className="w-6 h-6" />
                      </div>
                      <div className="text-right">
                        <div className="text-2xl font-bold text-gray-800">{Math.round((hardware.elements.firingCount / hardware.elements.maxLife) * 100)}%</div>
                      </div>
                    </div>
                    <h3 className="text-gray-700 text-sm font-medium">Element Health</h3>
                    <p className="text-gray-600 text-xs mt-2">{hardware.elements.firingCount}/{hardware.elements.maxLife} firings</p>
                  </div>

                  <div className="bg-gradient-to-br from-purple-500 to-indigo-500 rounded-2xl p-6 text-white shadow-xl">
                    <div className="flex items-center justify-between mb-4">
                      <div className="p-2 bg-white/20 rounded-lg">
                        <Calculator className="w-6 h-6" />
                      </div>
                      <Thermometer className="w-8 h-8 opacity-50" />
                    </div>
                    <h3 className="text-white/80 text-sm font-medium">Success Rate</h3>
                    <div className="text-3xl font-bold mt-2">
                      {firings.length > 0 ? Math.round(
                        (firings.filter(f => 
                          f.actualResult.toLowerCase().includes('perfect') || 
                          f.actualResult.toLowerCase().includes('good') ||
                          (f.actualResult.includes('cone') && f.actualResult.includes(f.targetCone.toString()) && !f.actualResult.toLowerCase().includes('hot'))
                        ).length / firings.length) * 100
                      ) : 0}%
                    </div>
                  </div>
                </div>

                {/* Smart Suggestions */}
                {suggestedOffsets && (
                  <div className="bg-gradient-to-r from-blue-50 to-indigo-100 rounded-2xl p-6 border border-blue-200">
                    <div className="flex items-center gap-3 mb-4">
                      <div className="p-2 bg-blue-500 rounded-lg">
                        <Calculator className="w-5 h-5 text-white" />
                      </div>
                      <h3 className="text-xl font-bold text-blue-900">Smart Offset Suggestions</h3>
                    </div>
                    <div className="grid md:grid-cols-3 gap-4">
                      {['top', 'middle', 'bottom'].map(zone => (
                        <div key={zone} className="bg-white rounded-xl p-4 shadow-sm">
                          <div className="flex justify-between items-center mb-2">
                            <span className="font-medium capitalize text-gray-700">{zone} Zone</span>
                            <span className="text-2xl font-bold text-blue-600">{suggestedOffsets[zone]}°F</span>
                          </div>
                          {suggestedOffsets[zone] !== zoneOffsets[zone] && (
                            <button
                              onClick={() => setZoneOffsets(prev => ({ ...prev, [zone]: suggestedOffsets[zone] }))}
                              className="w-full mt-2 px-3 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors text-sm"
                            >
                              Apply Suggestion
                            </button>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Add New Firing */}
                <div className="bg-gradient-to-br from-white to-gray-50 rounded-2xl border-2 border-dashed border-gray-300 p-8 shadow-lg">
                  <h2 className="text-2xl font-bold mb-6 flex items-center gap-3 text-gray-800">
                    <div className="p-2 bg-orange-500 rounded-lg">
                      <Plus className="w-6 h-6 text-white" />
                    </div>
                    Log New Firing
                  </h2>
                  
                  <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6 mb-6">
                    <div>
                      <label className="block text-sm font-semibold text-gray-700 mb-2">Target Cone</label>
                      <select
                        value={targetCone}
                        onChange={(e) => setTargetCone(e.target.value)}
                        className="w-full px-4 py-3 border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-orange-500 bg-white shadow-sm"
                      >
                        {Object.keys(coneTemps).map(cone => (
                          <option key={cone} value={cone}>Cone {cone}</option>
                        ))}
                      </select>
                    </div>
                    
                    <div>
                      <label className="block text-sm font-semibold text-gray-700 mb-2">Firing Type</label>
                      <select
                        value={firingType}
                        onChange={(e) => setFiringType(e.target.value)}
                        className="w-full px-4 py-3 border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-orange-500 bg-white shadow-sm"
                      >
                        <option value="bisque">Bisque</option>
                        <option value="glaze">Glaze</option>
                        <option value="test">Test</option>
                      </select>
                    </div>

                    <div>
                      <label className="block text-sm font-semibold text-gray-700 mb-2">Clay Body</label>
                      <select
                        value={clayBody}
                        onChange={(e) => setClayBody(e.target.value)}
                        className="w-full px-4 py-3 border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-orange-500 bg-white shadow-sm"
                      >
                        <option value="">Select clay...</option>
                        {clayBodies.map(clay => (
                          <option key={clay} value={clay}>{clay}</option>
                        ))}
                      </select>
                    </div>

                    <div>
                      <label className="block text-sm font-semibold text-gray-700 mb-2">Load Density</label>
                      <select
                        value={loadDensity}
                        onChange={(e) => setLoadDensity(e.target.value)}
                        className="w-full px-4 py-3 border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-orange-500 bg-white shadow-sm"
                      >
                        <option value="full">Full Load</option>
                        <option value="partial">Partial Load</option>
                        <option value="test">Test Load</option>
                      </select>
                    </div>
                  </div>

                  <div className="grid md:grid-cols-2 gap-6 mb-6">
                    <div>
                      <label className="block text-sm font-semibold text-gray-700 mb-2">Overall Result</label>
                      <input
                        type="text"
                        value={actualResult}
                        onChange={(e) => setActualResult(e.target.value)}
                        placeholder="e.g., 'hot cone 6', 'cone 7', 'perfect cone 6'"
                        className="w-full px-4 py-3 border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-orange-500 bg-white shadow-sm"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-semibold text-gray-700 mb-2">Glaze Type (optional)</label>
                      <input
                        type="text"
                        value={glazeType}
                        onChange={(e) => setGlazeType(e.target.value)}
                        placeholder="e.g., 'Clear', 'Celadon', 'Matte Black'"
                        className="w-full px-4 py-3 border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-orange-500 bg-white shadow-sm"
                      />
                    </div>
                  </div>

                  <div className="grid md:grid-cols-3 gap-6 mb-6">
                    <div>
                      <label className="block text-sm font-semibold text-gray-700 mb-2">Top Zone Result</label>
                      <input
                        type="text"
                        value={zoneResults.top}
                        onChange={(e) => setZoneResults(prev => ({ ...prev, top: e.target.value }))}
                        placeholder="Optional zone-specific result"
                        className="w-full px-4 py-3 border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-orange-500 bg-white shadow-sm"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-semibold text-gray-700 mb-2">Middle Zone Result</label>
                      <input
                        type="text"
                        value={zoneResults.middle}
                        onChange={(e) => setZoneResults(prev => ({ ...prev, middle: e.target.value }))}
                        placeholder="Optional zone-specific result"
                        className="w-full px-4 py-3 border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-orange-500 bg-white shadow-sm"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-semibold text-gray-700 mb-2">Bottom Zone Result</label>
                      <input
                        type="text"
                        value={zoneResults.bottom}
                        onChange={(e) => setZoneResults(prev => ({ ...prev, bottom: e.target.value }))}
                        placeholder="Optional zone-specific result"
                        className="w-full px-4 py-3 border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-orange-500 bg-white shadow-sm"
                      />
                    </div>
                  </div>
                  
                  <div className="mb-6">
                    <label className="block text-sm font-semibold text-gray-700 mb-2">Notes</label>
                    <textarea
                      value={notes}
                      onChange={(e) => setNotes(e.target.value)}
                      placeholder="Any observations about the firing..."
                      rows="3"
                      className="w-full px-4 py-3 border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-orange-500 bg-white shadow-sm"
                    />
                  </div>
                  
                  <button
                    onClick={addFiring}
                    disabled={!actualResult.trim()}
                    className="flex items-center gap-3 px-8 py-4 bg-gradient-to-r from-orange-500 to-red-500 text-white rounded-xl hover:from-orange-600 hover:to-red-600 disabled:from-gray-400 disabled:to-gray-500 disabled:cursor-not-allowed shadow-lg transition-all duration-200 font-semibold"
                  >
                    <Save className="w-5 h-5" />
                    Log Firing
                  </button>
                </div>

                {/* Firing History */}
                <div className="bg-white rounded-2xl shadow-lg border border-gray-100 p-8">
                  <h2 className="text-2xl font-bold mb-6 text-gray-800">Recent Firings</h2>
                  {firings.length === 0 ? (
                    <div className="text-center py-12">
                      <Flame className="w-16 h-16 text-gray-300 mx-auto mb-4" />
                      <p className="text-gray-500 text-lg">No firings logged yet.</p>
                      <p className="text-gray-400 text-sm">Start by logging your first firing above!</p>
                    </div>
                  ) : (
                    <div className="space-y-4">
                      {firings.slice(0, 10).map(firing => (
                        <div key={firing.id} className="bg-gradient-to-r from-gray-50 to-white rounded-xl border border-gray-200 p-6 hover:shadow-md transition-all duration-200">
                          <div className="flex justify-between items-start mb-4">
                            <div className="flex items-center gap-6 flex-wrap">
                              <span className="text-sm text-gray-500 font-medium">{firing.date} {firing.time}</span>
                              <span className="px-3 py-1 bg-gradient-to-r from-blue-500 to-purple-500 text-white rounded-full text-xs font-semibold">{firing.firingType}</span>
                              <span className="text-sm font-medium">Target: <span className="text-orange-600 font-bold">Cone {firing.targetCone}</span></span>
                              {firing.clayBody && <span className="text-xs text-gray-600 bg-gray-100 px-2 py-1 rounded-full">{firing.clayBody}</span>}
                            </div>
                          </div>
                          
                          <div className="grid md:grid-cols-2 gap-6 mb-4">
                            <div>
                              <span className="text-sm text-gray-600">Result: </span>
                              <span className="font-semibold text-gray-800">{firing.actualResult}</span>
                            </div>
                            <div className="text-sm">
                              <span className="text-gray-600">Zone Offsets: </span>
                              <span className="font-mono font-medium">T:{firing.zoneOffsets.top}° M:{firing.zoneOffsets.middle}° B:{firing.zoneOffsets.bottom}°</span>
                            </div>
                          </div>
                          
                          {(firing.zoneResults.top || firing.zoneResults.middle || firing.zoneResults.bottom) && (
                            <div className="text-sm text-gray-600 mb-3 bg-blue-50 rounded-lg p-3">
                              <span className="font-semibold text-blue-800">Zone Results: </span>
                              {firing.zoneResults.top && `Top: ${firing.zoneResults.top} `}
                              {firing.zoneResults.middle && `Middle: ${firing.zoneResults.middle} `}
                              {firing.zoneResults.bottom && `Bottom: ${firing.zoneResults.bottom}`}
                            </div>
                          )}
                          
                          {firing.notes && <p className="text-sm text-gray-600 italic bg-gray-50 rounded-lg p-3">{firing.notes}</p>}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            )}

            {activeTab === 'zones' && (
              <div className="space-y-8">
                <div className="text-center mb-8">
                  <h2 className="text-3xl font-bold text-gray-800 mb-2">Zone Control Center</h2>
                  <p className="text-gray-600">Manage individual zone offsets for precise firing control</p>
                </div>
                
                {/* Current Offsets */}
                <div className="grid md:grid-cols-3 gap-8">
                  {['top', 'middle', 'bottom'].map((zone, index) => {
                    const colors = ['from-red-500 to-orange-500', 'from-blue-500 to-cyan-500', 'from-green-500 to-emerald-500'];
                    return (
                      <div key={zone} className="bg-white rounded-2xl shadow-xl border border-gray-100 overflow-hidden">
                        <div className={`bg-gradient-to-r ${colors[index]} p-6 text-white`}>
                          <h3 className="text-xl font-bold capitalize mb-2 break-words">{zone} Zone</h3>
                          <div className="text-3xl font-bold">{zoneOffsets[zone]}°F</div>
                        </div>
                        <div className="p-6">
                          <div className="space-y-4">
                            <div>
                              <label className="block text-sm font-semibold text-gray-700 mb-2 break-words">Current Offset (°F)</label>
                              <input
                                type="number"
                                value={zoneOffsets[zone]}
                                onChange={(e) => setZoneOffsets(prev => ({ ...prev, [zone]: parseInt(e.target.value) || 0 }))}
                                className="w-full px-4 py-3 border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 text-center text-xl font-bold"
                              />
                            </div>
                            {suggestedOffsets && suggestedOffsets[zone] !== zoneOffsets[zone] && (
                              <div className="bg-gradient-to-r from-blue-50 to-indigo-50 rounded-xl p-4 border border-blue-200">
                                <p className="text-sm font-semibold text-blue-800 mb-2 break-words">AI Suggestion: {suggestedOffsets[zone]}°F</p>
                                <button
                                  onClick={() => setZoneOffsets(prev => ({ ...prev, [zone]: suggestedOffsets[zone] }))}
                                  className="w-full px-4 py-2 bg-gradient-to-r from-blue-500 to-indigo-500 text-white rounded-lg hover:from-blue-600 hover:to-indigo-600 transition-all duration-200 text-sm font-semibold break-words"
                                >
                                  Apply Suggestion
                                </button>
                              </div>
                            )}
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>

                {/* Zone Performance Chart */}
                <div className="bg-white rounded-2xl shadow-lg border border-gray-100 p-8">
                  <h3 className="text-xl font-bold text-gray-800 mb-6">Recent Zone Performance</h3>
                  {firings.length > 0 ? (
                    <div className="space-y-4">
                      {firings.slice(0, 5).map((firing, index) => (
                        <div key={firing.id} className="flex items-center gap-6 p-4 bg-gradient-to-r from-gray-50 to-white rounded-xl border border-gray-200">
                          <span className="w-24 text-sm text-gray-500 font-medium">{firing.date}</span>
                          <span className="w-20 text-sm font-semibold">Cone {firing.targetCone}</span>
                          <div className="flex gap-6 flex-1">
                            <span className="px-3 py-1 bg-red-100 text-red-800 rounded-full text-sm font-medium">T: {firing.zoneOffsets.top}°</span>
                            <span className="px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-sm font-medium">M: {firing.zoneOffsets.middle}°</span>
                            <span className="px-3 py-1 bg-green-100 text-green-800 rounded-full text-sm font-medium">B: {firing.zoneOffsets.bottom}°</span>
                          </div>
                          <span className="text-gray-600 font-medium">{firing.actualResult}</span>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="text-center py-8">
                      <Target className="w-12 h-12 text-gray-300 mx-auto mb-4" />
                      <p className="text-gray-500">No firing data yet.</p>
                    </div>
                  )}
                </div>
              </div>
            )}

            {activeTab === 'programs' && (
              <div className="space-y-8">
                <div className="text-center mb-8">
                  <h2 className="text-3xl font-bold text-gray-800 mb-2">Firing Programs</h2>
                  <p className="text-gray-600">Create and manage custom firing schedules</p>
                </div>
                
                {/* Add New Program */}
                <div className="bg-gradient-to-br from-purple-50 to-indigo-100 rounded-2xl border-2 border-dashed border-purple-300 p-8">
                  <h3 className="text-xl font-bold mb-6 flex items-center gap-3 text-purple-800">
                    <div className="p-2 bg-purple-500 rounded-lg">
                      <Plus className="w-5 h-5 text-white" />
                    </div>
                    Create New Program
                  </h3>
                  <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6 mb-6">
                    <div>
                      <label className="block text-sm font-semibold text-gray-700 mb-2">Program Name</label>
                      <input
                        type="text"
                        value={newProgram.name}
                        onChange={(e) => setNewProgram(prev => ({ ...prev, name: e.target.value }))}
                        placeholder="e.g., Cone 6 Slow Glaze"
                        className="w-full px-4 py-3 border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-purple-500 bg-white"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-semibold text-gray-700 mb-2">Type</label>
                      <select
                        value={newProgram.type}
                        onChange={(e) => setNewProgram(prev => ({ ...prev, type: e.target.value }))}
                        className="w-full px-4 py-3 border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-purple-500 bg-white"
                      >
                        <option value="bisque">Bisque</option>
                        <option value="glaze">Glaze</option>
                        <option value="test">Test</option>
                      </select>
                    </div>
                    <div>
                      <label className="block text-sm font-semibold text-gray-700 mb-2">Target Temp (°F)</label>
                      <input
                        type="number"
                        value={newProgram.targetTemp}
                        onChange={(e) => setNewProgram(prev => ({ ...prev, targetTemp: parseInt(e.target.value) || 0 }))}
                        className="w-full px-4 py-3 border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-purple-500 bg-white"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-semibold text-gray-700 mb-2">Ramp Rate (°F/hr)</label>
                      <input
                        type="number"
                        value={newProgram.rampRate}
                        onChange={(e) => setNewProgram(prev => ({ ...prev, rampRate: parseInt(e.target.value) || 0 }))}
                        className="w-full px-4 py-3 border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-purple-500 bg-white"
                      />
                    </div>
                  </div>
                  <div className="grid md:grid-cols-3 gap-6 mb-6">
                    <div>
                      <label className="block text-sm font-semibold text-gray-700 mb-2">Hold Time (min)</label>
                      <input
                        type="number"
                        value={newProgram.holdTime}
                        onChange={(e) => setNewProgram(prev => ({ ...prev, holdTime: parseInt(e.target.value) || 0 }))}
                        className="w-full px-4 py-3 border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-purple-500 bg-white"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-semibold text-gray-700 mb-2">Recommended Clay</label>
                      <select
                        value={newProgram.clayBody}
                        onChange={(e) => setNewProgram(prev => ({ ...prev, clayBody: e.target.value }))}
                        className="w-full px-4 py-3 border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-purple-500 bg-white"
                      >
                        <option value="">Any clay...</option>
                        {clayBodies.map(clay => (
                          <option key={clay} value={clay}>{clay}</option>
                        ))}
                      </select>
                    </div>
                    <div className="flex items-end">
                      <button
                        onClick={addProgram}
                        disabled={!newProgram.name.trim()}
                        className="w-full px-6 py-3 bg-gradient-to-r from-purple-500 to-indigo-500 text-white rounded-xl hover:from-purple-600 hover:to-indigo-600 disabled:from-gray-400 disabled:to-gray-500 font-semibold shadow-lg transition-all duration-200"
                      >
                        Save Program
                      </button>
                    </div>
                  </div>
                </div>

                {/* Saved Programs */}
                <div>
                  <h3 className="text-xl font-bold mb-6 text-gray-800">Saved Programs</h3>
                  {programs.length === 0 ? (
                    <div className="text-center py-12 bg-white rounded-2xl border border-gray-200">
                      <Settings className="w-16 h-16 text-gray-300 mx-auto mb-4" />
                      <p className="text-gray-500 text-lg">No programs saved yet.</p>
                      <p className="text-gray-400 text-sm">Create your first firing program above!</p>
                    </div>
                  ) : (
                    <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
                      {programs.map(program => (
                        <div key={program.id} className="bg-white rounded-2xl shadow-lg border border-gray-100 overflow-hidden hover:shadow-xl transition-shadow duration-200">
                          <div className="bg-gradient-to-r from-purple-500 to-indigo-500 p-4 text-white">
                            <div className="flex justify-between items-start mb-2">
                              <h4 className="font-bold text-lg">{program.name}</h4>
                              <span className="px-2 py-1 bg-white/20 rounded-full text-xs font-semibold">{program.type}</span>
                            </div>
                          </div>
                          <div className="p-6">
                            <div className="space-y-3 text-sm">
                              <div className="flex justify-between">
                                <span className="text-gray-600">Target:</span>
                                <span className="font-semibold">{program.targetTemp}°F</span>
                              </div>
                              <div className="flex justify-between">
                                <span className="text-gray-600">Ramp:</span>
                                <span className="font-semibold">{program.rampRate}°F/hr</span>
                              </div>
                              <div className="flex justify-between">
                                <span className="text-gray-600">Hold:</span>
                                <span className="font-semibold">{program.holdTime} min</span>
                              </div>
                              {program.clayBody && (
                                <div className="mt-3 pt-3 border-t border-gray-200">
                                  <span className="text-xs text-gray-500">Recommended Clay:</span>
                                  <p className="font-medium text-sm">{program.clayBody}</p>
                                </div>
                              )}
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            )}

            {activeTab === 'hardware' && (
              <div className="space-y-8">
                <div className="text-center mb-8">
                  <h2 className="text-3xl font-bold text-gray-800 mb-2">Hardware Maintenance</h2>
                  <p className="text-gray-600">Monitor and maintain your kiln components</p>
                </div>
                
                {/* Hardware Status */}
                <div className="grid md:grid-cols-3 gap-8">
                  {Object.entries(hardware).map(([component, data]) => {
                    const health = getHealthStatus(data);
                    const usagePercent = (data.firingCount / data.maxLife) * 100;
                    
                    return (
                      <div key={component} className={`${health.bg} rounded-2xl shadow-xl overflow-hidden border-2 ${health.ring}`}>
                        <div className="p-6">
                          <div className="flex items-center gap-3 mb-4">
                            <div className="p-3 bg-white/20 rounded-xl">
                              <Zap className="w-6 h-6 text-gray-700" />
                            </div>
                            <h3 className="text-xl font-bold capitalize text-gray-800">{component}</h3>
                          </div>
                          
                          <div className="space-y-4">
                            <div>
                              <label className="block text-sm font-semibold text-gray-700 mb-2">Install Date</label>
                              <input
                                type="date"
                                value={data.installed}
                                onChange={(e) => setHardware(prev => ({
                                  ...prev,
                                  [component]: { ...prev[component], installed: e.target.value }
                                }))}
                                className="w-full px-4 py-3 border border-gray-200 rounded-xl text-sm bg-white"
                              />
                            </div>
                            
                            <div>
                              <label className="block text-sm font-semibold text-gray-700 mb-2">Firing Count</label>
                              <input
                                type="number"
                                value={data.firingCount}
                                onChange={(e) => setHardware(prev => ({
                                  ...prev,
                                  [component]: { ...prev[component], firingCount: parseInt(e.target.value) || 0 }
                                }))}
                                className="w-full px-4 py-3 border border-gray-200 rounded-xl text-sm bg-white font-bold text-center"
                              />
                            </div>
                            
                            <div>
                              <label className="block text-sm font-semibold text-gray-700 mb-2">Expected Life</label>
                              <input
                                type="number"
                                value={data.maxLife}
                                onChange={(e) => setHardware(prev => ({
                                  ...prev,
                                  [component]: { ...prev[component], maxLife: parseInt(e.target.value) || 0 }
                                }))}
                                className="w-full px-4 py-3 border border-gray-200 rounded-xl text-sm bg-white"
                              />
                            </div>
                            
                            <div className="pt-4">
                              <div className="flex justify-between text-sm mb-2">
                                <span className="font-semibold">Usage</span>
                                <span className={`font-bold ${health.color}`}>{Math.round(usagePercent)}%</span>
                              </div>
                              <div className="w-full bg-white/50 rounded-full h-3 overflow-hidden">
                                <div 
                                  className={`h-3 rounded-full transition-all duration-500 ${
                                    usagePercent < 60 ? 'bg-gradient-to-r from-green-400 to-emerald-500' : 
                                    usagePercent < 85 ? 'bg-gradient-to-r from-yellow-400 to-orange-500' : 'bg-gradient-to-r from-red-400 to-red-600'
                                  }`}
                                  style={{ width: `${Math.min(usagePercent, 100)}%` }}
                                />
                              </div>
                              <div className={`text-sm font-bold mt-2 ${health.color}`}>
                                {health.status}
                              </div>
                            </div>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>

                {/* Maintenance Alerts */}
                <div className="bg-white rounded-2xl shadow-lg border border-gray-100 p-8">
                  <h3 className="text-xl font-bold mb-6 flex items-center gap-3 text-gray-800">
                    <div className="p-2 bg-yellow-500 rounded-lg">
                      <Bell className="w-5 h-5 text-white" />
                    </div>
                    Maintenance Alerts
                  </h3>
                  <div className="space-y-4">
                    {Object.entries(hardware).map(([component, data]) => {
                      const usagePercent = (data.firingCount / data.maxLife) * 100;
                      if (usagePercent < 60) return null;
                      
                      return (
                        <div key={component} className={`p-4 rounded-xl border-l-4 ${
                          usagePercent >= 85 ? 'bg-red-50 border-red-500 text-red-800' : 'bg-yellow-50 border-yellow-500 text-yellow-800'
                        }`}>
                          <div className="flex items-center gap-3">
                            <Wrench className="w-5 h-5" />
                            <div>
                              <span className="font-bold capitalize">{component}:</span> {
                                usagePercent >= 85 ? 'Replacement recommended soon' : 'Monitor closely'
                              }
                              <div className="text-sm opacity-75">({Math.round(usagePercent)}% used)</div>
                            </div>
                          </div>
                        </div>
                      );
                    })}
                    {Object.values(hardware).every(data => (data.firingCount / data.maxLife) * 100 < 60) && (
                      <div className="text-center py-8">
                        <div className="inline-flex items-center gap-3 px-6 py-3 bg-green-50 text-green-800 rounded-xl border border-green-200">
                          <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
                          <span className="font-semibold">All hardware in excellent condition!</span>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )}

            {activeTab === 'analytics' && (
              <div className="space-y-8">
                <div className="text-center mb-8">
                  <h2 className="text-3xl font-bold text-gray-800 mb-2">Firing Analytics</h2>
                  <p className="text-gray-600">Insights and trends from your firing data</p>
                </div>
                
                {firings.length === 0 ? (
                  <div className="text-center py-16 bg-white rounded-2xl border border-gray-200">
                    <BarChart3 className="w-20 h-20 text-gray-300 mx-auto mb-6" />
                    <p className="text-gray-500 text-xl mb-2">No data available yet</p>
                    <p className="text-gray-400">Log some firings to see detailed analytics!</p>
                  </div>
                ) : (
                  <div className="space-y-8">
                    {/* Key Metrics */}
                    <div className="grid md:grid-cols-4 gap-6">
                      <div className="bg-gradient-to-br from-green-500 to-emerald-500 rounded-2xl p-6 text-white shadow-xl">
                        <div className="flex items-center justify-between mb-4">
                          <div className="p-2 bg-white/20 rounded-lg">
                            <TrendingUp className="w-6 h-6" />
                          </div>
                          <div className="text-3xl font-bold">
                            {Math.round(
                              (firings.filter(f => 
                                f.actualResult.toLowerCase().includes('perfect') || 
                                f.actualResult.toLowerCase().includes('good') ||
                                (f.actualResult.includes('cone') && f.actualResult.includes(f.targetCone.toString()) && !f.actualResult.toLowerCase().includes('hot'))
                              ).length / firings.length) * 100
                            )}%
                          </div>
                        </div>
                        <h3 className="text-white/80 text-sm font-medium">Success Rate</h3>
                        <p className="text-white/60 text-xs mt-1">Perfect firings</p>
                      </div>
                      
                      <div className="bg-gradient-to-br from-orange-500 to-red-500 rounded-2xl p-6 text-white shadow-xl">
                        <div className="flex items-center justify-between mb-4">
                          <div className="p-2 bg-white/20 rounded-lg">
                            <Target className="w-6 h-6" />
                          </div>
                          <div className="text-3xl font-bold">
                            {Math.round(
                              firings.reduce((sum, f) => sum + f.zoneOffsets.middle, 0) / firings.length
                            )}°F
                          </div>
                        </div>
                        <h3 className="text-white/80 text-sm font-medium">Average Offset</h3>
                        <p className="text-white/60 text-xs mt-1">Middle zone</p>
                      </div>
                      
                      <div className="bg-gradient-to-br from-blue-500 to-cyan-500 rounded-2xl p-6 text-white shadow-xl">
                        <div className="flex items-center justify-between mb-4">
                          <div className="p-2 bg-white/20 rounded-lg">
                            <Flame className="w-6 h-6" />
                          </div>
                          <div className="text-3xl font-bold">
                            {(() => {
                              const counts = firings.filter(f => f.clayBody).reduce((acc, f) => {
                                acc[f.clayBody] = (acc[f.clayBody] || 0) + 1;
                                return acc;
                              }, {});
                              return Object.keys(counts).length > 0 ? 
                                Object.keys(counts).reduce((a, b) => counts[a] > counts[b] ? a : b).split(' ')[0] : 
                                'None';
                            })()}
                          </div>
                        </div>
                        <h3 className="text-white/80 text-sm font-medium">Top Clay</h3>
                        <p className="text-white/60 text-xs mt-1">Most used</p>
                      </div>

                      <div className="bg-gradient-to-br from-purple-500 to-indigo-500 rounded-2xl p-6 text-white shadow-xl">
                        <div className="flex items-center justify-between mb-4">
                          <div className="p-2 bg-white/20 rounded-lg">
                            <Activity className="w-6 h-6" />
                          </div>
                          <div className="text-3xl font-bold">{firings.length}</div>
                        </div>
                        <h3 className="text-white/80 text-sm font-medium">Total Firings</h3>
                        <p className="text-white/60 text-xs mt-1">All time</p>
                      </div>
                    </div>

                    {/* Zone Offset Trends */}
                    <div className="bg-white rounded-2xl shadow-lg border border-gray-100 p-8">
                      <h3 className="text-xl font-bold mb-6 text-gray-800">Zone Offset Trends</h3>
                      <div className="space-y-6">
                        {['top', 'middle', 'bottom'].map((zone, index) => {
                          const recentOffsets = firings.slice(0, 10).map(f => f.zoneOffsets[zone]);
                          const avgOffset = recentOffsets.reduce((a, b) => a + b, 0) / recentOffsets.length;
                          const colors = ['from-red-400 to-orange-500', 'from-blue-400 to-cyan-500', 'from-green-400 to-emerald-500'];
                          
                          return (
                            <div key={zone} className="flex items-center gap-6">
                              <span className="w-20 capitalize font-bold text-gray-700">{zone}:</span>
                              <div className="flex-1 bg-gray-100 rounded-full h-4 relative overflow-hidden">
                                <div 
                                  className={`bg-gradient-to-r ${colors[index]} h-4 rounded-full transition-all duration-500`}
                                  style={{ width: `${(avgOffset / 100) * 100}%` }}
                                />
                                <span className="absolute right-3 top-0 text-xs text-gray-700 font-semibold leading-4">
                                  {Math.round(avgOffset)}°F avg
                                </span>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    </div>

                    {/* Firing Type Distribution */}
                    <div className="bg-white rounded-2xl shadow-lg border border-gray-100 p-8">
                      <h3 className="text-xl font-bold mb-6 text-gray-800">Firing Type Distribution</h3>
                      <div className="grid grid-cols-3 gap-6">
                        {['bisque', 'glaze', 'test'].map((type, index) => {
                          const count = firings.filter(f => f.firingType === type).length;
                          const percentage = (count / firings.length) * 100;
                          const colors = ['from-yellow-400 to-orange-500', 'from-blue-400 to-purple-500', 'from-green-400 to-cyan-500'];
                          
                          return (
                            <div key={type} className={`bg-gradient-to-br ${colors[index]} rounded-2xl p-6 text-white text-center shadow-lg`}>
                              <div className="text-3xl font-bold capitalize">{type}</div>
                              <div className="text-2xl font-semibold mt-2">{count}</div>
                              <div className="text-white/80 text-sm">({Math.round(percentage)}%)</div>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}

            {activeTab === 'help' && (
              <div className="space-y-8">
                <div className="text-center mb-8">
                  <h2 className="text-3xl font-bold text-gray-800 mb-2">Help & User Guide</h2>
                  <p className="text-gray-600">Learn how to master your kiln firing with KilnMaster Pro</p>
                </div>

                {/* Quick Start Guide */}
                <div className="bg-white rounded-2xl shadow-lg border border-gray-100 p-8">
                  <h3 className="text-2xl font-bold mb-6 text-gray-800 flex items-center gap-3">
                    <div className="p-2 bg-teal-500 rounded-lg">
                      <Flame className="w-6 h-6 text-white" />
                    </div>
                    Quick Start Guide
                  </h3>
                  
                  <div className="grid md:grid-cols-2 gap-8">
                    <div className="space-y-6">
                      <div className="bg-gradient-to-r from-orange-50 to-red-50 rounded-xl p-6 border border-orange-200">
                        <h4 className="font-bold text-orange-800 mb-3">1. Set Your Zone Offsets</h4>
                        <p className="text-gray-700 text-sm leading-relaxed">Start in the Zone Control tab. Set your initial offsets based on your kiln's current performance. Most kilns start around 18°F but yours may be different.</p>
                      </div>
                      
                      <div className="bg-gradient-to-r from-blue-50 to-cyan-50 rounded-xl p-6 border border-blue-200">
                        <h4 className="font-bold text-blue-800 mb-3">2. Log Your First Firing</h4>
                        <p className="text-gray-700 text-sm leading-relaxed">Use the Firing Log tab to record your firing results. Be specific: "hot cone 6", "cone 7", "perfect cone 6", etc. The more detail, the better the AI suggestions.</p>
                      </div>
                      
                      <div className="bg-gradient-to-r from-purple-50 to-indigo-50 rounded-xl p-6 border border-purple-200">
                        <h4 className="font-bold text-purple-800 mb-3">3. Track Your Hardware</h4>
                        <p className="text-gray-700 text-sm leading-relaxed">Go to Maintenance tab and set your element install date and current firing count. This helps predict when replacements are needed.</p>
                      </div>
                    </div>
                    
                    <div className="space-y-6">
                      <div className="bg-gradient-to-r from-green-50 to-emerald-50 rounded-xl p-6 border border-green-200">
                        <h4 className="font-bold text-green-800 mb-3">4. Use AI Suggestions</h4>
                        <p className="text-gray-700 text-sm leading-relaxed">After 2-3 firings, the app will suggest offset adjustments. These are based on your actual results and kiln behavior patterns.</p>
                      </div>
                      
                      <div className="bg-gradient-to-r from-pink-50 to-rose-50 rounded-xl p-6 border border-rose-200">
                        <h4 className="font-bold text-pink-800 mb-3">5. Analyze Your Progress</h4>
                        <p className="text-gray-700 text-sm leading-relaxed">Check the Analytics tab to see your success rate trends, most-used clay bodies, and firing patterns over time.</p>
                      </div>
                      
                      <div className="bg-gradient-to-r from-slate-50 to-gray-50 rounded-xl p-6 border border-slate-200">
                        <h4 className="font-bold text-slate-800 mb-3">6. Export Your Data</h4>
                        <p className="text-gray-700 text-sm leading-relaxed">Regular backups keep your firing history safe. Use the Export button to save your data for insurance or sharing with others.</p>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Troubleshooting */}
                <div className="bg-white rounded-2xl shadow-lg border border-gray-100 p-8">
                  <h3 className="text-2xl font-bold mb-6 text-gray-800">Common Firing Problems & Solutions</h3>
                  
                  <div className="space-y-6">
                    <div className="border-l-4 border-red-500 pl-6 py-4 bg-red-50 rounded-r-lg">
                      <h4 className="font-bold text-red-800 mb-2">🔥 Overfiring (Getting Cone 7 when targeting Cone 6)</h4>
                      <p className="text-red-700 mb-2"><strong>Solution:</strong> Increase your offset by 15-25°F. For severe overfiring (cone 8+), try 30-40°F increase.</p>
                      <p className="text-red-600 text-sm">L&L kilns can safely handle up to 100°F offset according to their tech support.</p>
                    </div>
                    
                    <div className="border-l-4 border-blue-500 pl-6 py-4 bg-blue-50 rounded-r-lg">
                      <h4 className="font-bold text-blue-800 mb-2">🧊 Underfiring (Getting soft cone 6 or cone 5)</h4>
                      <p className="text-blue-700 mb-2"><strong>Solution:</strong> Decrease your offset by 10-20°F. Check if your elements are aging or thermocouples drifting.</p>
                      <p className="text-blue-600 text-sm">New elements often fire hotter initially, requiring higher offsets that decrease over time.</p>
                    </div>
                    
                    <div className="border-l-4 border-yellow-500 pl-6 py-4 bg-yellow-50 rounded-r-lg">
                      <h4 className="font-bold text-yellow-800 mb-2">⚖️ Uneven Firing (Different zones firing differently)</h4>
                      <p className="text-yellow-700 mb-2"><strong>Solution:</strong> Use individual zone offsets. Top zones often need higher offsets due to heat rise.</p>
                      <p className="text-yellow-600 text-sm">Log zone-specific results to get targeted suggestions for each zone.</p>
                    </div>
                    
                    <div className="border-l-4 border-purple-500 pl-6 py-4 bg-purple-50 rounded-r-lg">
                      <h4 className="font-bold text-purple-800 mb-2">🔧 New Elements Firing Too Hot</h4>
                      <p className="text-purple-700 mb-2"><strong>Solution:</strong> Start with 50°F offset for brand new elements, then reduce by 5-10°F every 10 firings as they break in.</p>
                      <p className="text-purple-600 text-sm">Track this in the Hardware tab to predict when adjustments are needed.</p>
                    </div>
                  </div>
                </div>

                {/* Pro Tips */}
                <div className="bg-gradient-to-br from-teal-50 to-cyan-100 rounded-2xl border border-teal-200 p-8">
                  <h3 className="text-2xl font-bold mb-6 text-teal-800">Pro Tips for Perfect Firings</h3>
                  
                  <div className="grid md:grid-cols-2 gap-6">
                    <div className="space-y-4">
                      <div className="flex items-start gap-3">
                        <div className="w-6 h-6 bg-teal-500 rounded-full flex items-center justify-center text-white text-xs font-bold mt-1">1</div>
                        <div>
                          <h4 className="font-semibold text-teal-800">Use Witness Cones Always</h4>
                          <p className="text-teal-700 text-sm">Place cones throughout your kiln to verify digital controller accuracy.</p>
                        </div>
                      </div>
                      
                      <div className="flex items-start gap-3">
                        <div className="w-6 h-6 bg-teal-500 rounded-full flex items-center justify-center text-white text-xs font-bold mt-1">2</div>
                        <div>
                          <h4 className="font-semibold text-teal-800">Track Load Density</h4>
                          <p className="text-teal-700 text-sm">Full loads fire differently than partial loads. Log this for better predictions.</p>
                        </div>
                      </div>
                      
                      <div className="flex items-start gap-3">
                        <div className="w-6 h-6 bg-teal-500 rounded-full flex items-center justify-center text-white text-xs font-bold mt-1">3</div>
                        <div>
                          <h4 className="font-semibold text-teal-800">Document Everything</h4>
                          <p className="text-teal-700 text-sm">Notes about weather, kiln placement, or unusual observations help identify patterns.</p>
                        </div>
                      </div>
                    </div>
                    
                    <div className="space-y-4">
                      <div className="flex items-start gap-3">
                        <div className="w-6 h-6 bg-teal-500 rounded-full flex items-center justify-center text-white text-xs font-bold mt-1">4</div>
                        <div>
                          <h4 className="font-semibold text-teal-800">Slow Adjustments</h4>
                          <p className="text-teal-700 text-sm">Make 10-15°F changes at a time. Big jumps can overcorrect and cause new problems.</p>
                        </div>
                      </div>
                      
                      <div className="flex items-start gap-3">
                        <div className="w-6 h-6 bg-teal-500 rounded-full flex items-center justify-center text-white text-xs font-bold mt-1">5</div>
                        <div>
                          <h4 className="font-semibold text-teal-800">Test Regularly</h4>
                          <p className="text-teal-700 text-sm">Run test tiles with new glazes or clay bodies before committing finished pieces.</p>
                        </div>
                      </div>
                      
                      <div className="flex items-start gap-3">
                        <div className="w-6 h-6 bg-teal-500 rounded-full flex items-center justify-center text-white text-xs font-bold mt-1">6</div>
                        <div>
                          <h4 className="font-semibold text-teal-800">Backup Your Data</h4>
                          <p className="text-teal-700 text-sm">Export your firing history monthly. This data is valuable for insurance and troubleshooting.</p>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {activeTab === 'about' && (
              <div className="space-y-8">
                <div className="text-center mb-8">
                  <h2 className="text-3xl font-bold text-gray-800 mb-2">About KilnMaster Pro</h2>
                  <p className="text-gray-600">The story behind the world's most advanced kiln management system</p>
                </div>

                {/* Origin Story */}
                <div className="bg-white rounded-2xl shadow-lg border border-gray-100 p-8">
                  <div className="flex items-center gap-4 mb-6">
                    <div className="p-3 bg-gradient-to-br from-orange-500 to-red-500 rounded-2xl">
                      <Flame className="w-8 h-8 text-white" />
                    </div>
                    <div>
                      <h3 className="text-2xl font-bold text-gray-800">The Inspiration</h3>
                      <p className="text-gray-600">Born from real pottery studio frustrations</p>
                    </div>
                  </div>
                  
                  <div className="bg-gradient-to-r from-orange-50 to-red-50 rounded-xl p-6 border border-orange-200 mb-6">
                    <h4 className="font-bold text-orange-800 mb-3">💡 The Original Idea</h4>
                    <p className="text-gray-700 leading-relaxed mb-4">
                      KilnMaster Pro was inspired by <strong>Alford Wayman</strong> at <strong>Creek Road Pottery LLC</strong>, who shared insights about the universal challenges potters face with kiln management and helped identify the need for better firing documentation tools.
                    </p>
                    <p className="text-gray-700 leading-relaxed">
                      Though Alford works primarily with gas kilns, his observations about the pottery community's struggles with inconsistent firings, lost records, and maintenance tracking highlighted problems that span all kiln types. His humble suggestion that "maybe an app could help" sparked the creation of this comprehensive solution for electric kiln management.
                    </p>
                  </div>

                  <div className="grid md:grid-cols-2 gap-6">
                    <div className="bg-blue-50 rounded-xl p-6 border border-blue-200">
                      <h4 className="font-bold text-blue-800 mb-3">🎯 The Problem We Solve</h4>
                      <ul className="space-y-2 text-sm text-blue-700">
                        <li>• Kiln offset guesswork and trial-and-error</li>
                        <li>• Lost firing records and maintenance schedules</li>
                        <li>• Expensive element replacement surprises</li>
                        <li>• Inconsistent firing results across zones</li>
                        <li>• No data-driven insights for improvement</li>
                      </ul>
                    </div>
                    
                    <div className="bg-green-50 rounded-xl p-6 border border-green-200">
                      <h4 className="font-bold text-green-800 mb-3">✨ Our Solution</h4>
                      <ul className="space-y-2 text-sm text-green-700">
                        <li>• AI-powered offset recommendations</li>
                        <li>• Comprehensive firing and maintenance logs</li>
                        <li>• Predictive hardware replacement alerts</li>
                        <li>• Individual zone control and tracking</li>
                        <li>• Advanced analytics and trend analysis</li>
                      </ul>
                    </div>
                  </div>
                </div>

                {/* Features Overview */}
                <div className="bg-white rounded-2xl shadow-lg border border-gray-100 p-8">
                  <h3 className="text-2xl font-bold mb-6 text-gray-800">What Makes KilnMaster Pro Special</h3>
                  
                  <div className="grid md:grid-cols-3 gap-6">
                    <div className="text-center p-6 bg-gradient-to-br from-purple-50 to-indigo-100 rounded-xl border border-purple-200">
                      <div className="p-3 bg-purple-500 rounded-full w-fit mx-auto mb-4">
                        <Calculator className="w-8 h-8 text-white" />
                      </div>
                      <h4 className="font-bold text-purple-800 mb-2">Smart AI Predictions</h4>
                      <p className="text-purple-700 text-sm">Machine learning analyzes your firing patterns to suggest optimal offset adjustments.</p>
                    </div>
                    
                    <div className="text-center p-6 bg-gradient-to-br from-teal-50 to-cyan-100 rounded-xl border border-teal-200">
                      <div className="p-3 bg-teal-500 rounded-full w-fit mx-auto mb-4">
                        <Target className="w-8 h-8 text-white" />
                      </div>
                      <h4 className="font-bold text-teal-800 mb-2">Multi-Zone Control</h4>
                      <p className="text-teal-700 text-sm">Individual tracking for top, middle, and bottom zones for precision firing control.</p>
                    </div>
                    
                    <div className="text-center p-6 bg-gradient-to-br from-green-50 to-emerald-100 rounded-xl border border-green-200">
                      <div className="p-3 bg-green-500 rounded-full w-fit mx-auto mb-4">
                        <Wrench className="w-8 h-8 text-white" />
                      </div>
                      <h4 className="font-bold text-green-800 mb-2">Predictive Maintenance</h4>
                      <p className="text-green-700 text-sm">Never get surprised by element failure again with intelligent component lifecycle tracking.</p>
                    </div>
                  </div>
                </div>

                {/* Community & Credits */}
                <div className="bg-gradient-to-br from-slate-50 to-gray-100 rounded-2xl border border-slate-200 p-8">
                  <h3 className="text-2xl font-bold mb-6 text-slate-800">Community & Credits</h3>
                  
                  <div className="grid md:grid-cols-2 gap-8">
                    <div>
                      <h4 className="font-bold text-slate-800 mb-4 flex items-center gap-2">
                        <Users className="w-5 h-5" />
                        Special Thanks
                      </h4>
                      <div className="bg-white rounded-xl p-6 border border-slate-200">
                        <div className="flex items-center gap-4 mb-4">
                          <div className="w-12 h-12 bg-gradient-to-br from-orange-400 to-red-500 rounded-full flex items-center justify-center text-white font-bold text-lg">
                            AW
                          </div>
                          <div>
                            <h5 className="font-bold text-gray-800">Alford Wayman</h5>
                            <p className="text-gray-600 text-sm">Creek Road Pottery LLC</p>
                          </div>
                        </div>
                        <p className="text-gray-700 text-sm leading-relaxed">
                          The thoughtful observer who identified this need. Although Alford works with gas kilns rather than electric, his insights about the ceramic community's shared challenges with firing consistency and record-keeping helped inspire this digital solution. His humble suggestion to explore technology solutions opened the door to helping electric kiln users worldwide.
                        </p>
                      </div>
                    </div>
                    
                    <div>
                      <h4 className="font-bold text-slate-800 mb-4 flex items-center gap-2">
                        <Thermometer className="w-5 h-5" />
                        Technical Features
                      </h4>
                      <div className="space-y-3">
                        <div className="flex items-center gap-3 text-sm">
                          <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
                          <span className="text-gray-700">Browser-based data storage for privacy</span>
                        </div>
                        <div className="flex items-center gap-3 text-sm">
                          <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                          <span className="text-gray-700">Export functionality for data backup</span>
                        </div>
                        <div className="flex items-center gap-3 text-sm">
                          <div className="w-2 h-2 bg-purple-500 rounded-full"></div>
                          <span className="text-gray-700">Responsive design for mobile and desktop</span>
                        </div>
                        <div className="flex items-center gap-3 text-sm">
                          <div className="w-2 h-2 bg-orange-500 rounded-full"></div>
                          <span className="text-gray-700">Real-time analytics and trend analysis</span>
                        </div>
                        <div className="flex items-center gap-3 text-sm">
                          <div className="w-2 h-2 bg-teal-500 rounded-full"></div>
                          <span className="text-gray-700">Customizable firing programs and schedules</span>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Contact & Future */}
                <div className="bg-white rounded-2xl shadow-lg border border-gray-100 p-8 text-center">
                  <h3 className="text-2xl font-bold mb-4 text-gray-800">The Future of Ceramic Technology</h3>
                  <p className="text-gray-600 leading-relaxed mb-6">
                    KilnMaster Pro represents the collaborative spirit of the ceramic community. By combining traditional pottery wisdom 
                    with modern analytics, we're helping electric kiln users achieve consistent, professional results while preserving the joy 
                    and creativity that makes ceramics so special. Special thanks to those like Alford who help identify opportunities to assist fellow artists.
                  </p>
                  <div className="inline-flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-orange-500 to-red-500 text-white rounded-xl shadow-lg">
                    <Flame className="w-5 h-5" />
                    <span className="font-semibold">Made with ❤️ for the Ceramic Community</span>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default KilnOffsetTracker;
