'use client';

import { useState, useEffect } from 'react';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export default function DashboardPage() {
    const [sites, setSites] = useState([]);
    const [chats, setChats] = useState([]);
    const [analytics, setAnalytics] = useState(null);
    const [selectedSite, setSelectedSite] = useState(null);

    const [newSiteName, setNewSiteName] = useState('');
    const [newSiteDomain, setNewSiteDomain] = useState('');

    async function fetchSites() {
        const res = await fetch(`${API_URL}/api/dashboard/sites`);
        const data = await res.json();
        setSites(data);
    }

    async function fetchChats(siteId) {
        const res = await fetch(`${API_URL}/api/dashboard/sites/${siteId}/chats`);
        const data = await res.json();
        setChats(data);
    }

    async function fetchAnalytics(siteId) {
        const res = await fetch(`${API_URL}/api/dashboard/sites/${siteId}/analytics`);
        const data = await res.json();
        setAnalytics(data);
    }

    async function handleCreateSite() {
        if (!newSiteName || !newSiteDomain) {
            alert('Please enter a name and domain for the site.');
            return;
        }

        await fetch(`${API_URL}/api/dashboard/sites`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name: newSiteName, domain: newSiteDomain })
        });

        setNewSiteName('');
        setNewSiteDomain('');
        fetchSites();
    }

    useEffect(() => {
        fetchSites();
    }, []);

    const handleSiteSelection = (site) => {
        setSelectedSite(site);
        fetchChats(site._id);
        fetchAnalytics(site._id);
    };

    return (
        <div className="dark min-h-screen bg-gray-900 text-white p-8">
            <div className="max-w-7xl mx-auto">
                <h1 className="text-4xl font-bold mb-8">AI Concierge Dashboard</h1>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
                    <div className="md:col-span-1 bg-gray-800 p-6 rounded-lg">
                        <h2 className="text-2xl font-bold mb-4">Create New Site</h2>
                        <div className="space-y-4">
                            <input
                                type="text"
                                placeholder="Site Name"
                                value={newSiteName}
                                onChange={(e) => setNewSiteName(e.target.value)}
                                className="w-full bg-gray-700 text-white rounded-md px-4 py-2 focus:outline-none focus:ring-2 focus:ring-primary"
                            />
                            <input
                                type="text"
                                placeholder="Site Domain (e.g., example.com)"
                                value={newSiteDomain}
                                onChange={(e) => setNewSiteDomain(e.target.value)}
                                className="w-full bg-gray-700 text-white rounded-md px-4 py-2 focus:outline-none focus:ring-2 focus:ring-primary"
                            />
                            <button
                                onClick={handleCreateSite}
                                className="w-full bg-primary text-primary-foreground px-4 py-2 rounded-md hover:bg-primary/90"
                            >
                                Create Site
                            </button>
                        </div>
                        <hr className="my-6 border-gray-700" />
                        <h2 className="text-2xl font-bold mb-4">Sites</h2>
                        <ul className="space-y-2">
                            {sites.map(site => (
                                <li key={site._id}>
                                    <button
                                        onClick={() => handleSiteSelection(site)}
                                        className={`w-full text-left px-4 py-2 rounded-md ${selectedSite?._id === site._id ? 'bg-primary text-primary-foreground' : 'bg-gray-700 hover:bg-gray-600'}`}>
                                        {site.name}
                                    </button>
                                </li>
                            ))}
                        </ul>
                    </div>

                    <div className="md:col-span-2 bg-gray-800 p-6 rounded-lg">
                        {selectedSite ? (
                            <div>
                                <h2 className="text-3xl font-bold mb-6">{selectedSite.name}</h2>
                                <div className="mb-8">
                                    <h3 className="text-2xl font-bold mb-4">Analytics</h3>
                                    {analytics ? (
                                        <p>Total Chats: {analytics.num_chats}</p>
                                    ) : (
                                        <p>Loading analytics...</p>
                                    )}
                                </div>
                                <div>
                                    <h3 className="text-2xl font-bold mb-4">Chat Logs</h3>
                                    <div className="space-y-4 max-h-96 overflow-y-auto">
                                        {chats.length > 0 ? (
                                            chats.map(chat => (
                                                <div key={chat._id} className="bg-gray-700 p-4 rounded-md">
                                                    <p><strong>User:</strong> {chat.user_message}</p>
                                                    <p><strong>Bot:</strong> {chat.ai_result.note}</p>
                                                </div>
                                            ))
                                        ) : (
                                            <p>No chats yet for this site.</p>
                                        )}
                                    </div>
                                </div>
                            </div>
                        ) : (
                            <div className="flex items-center justify-center h-full">
                                <p className="text-gray-400">Select a site to view its details</p>
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}
