// frontend/src/integrations/hubspot.js

import React from "react";
import { useEffect, useState } from "react";
import axios from "axios";

const HubSpotIntegration = ({ userId, orgId }) => {
    const [authUrl, setAuthUrl] = useState("");

    useEffect(() => {
        const fetchAuthUrl = async () => {
            const response = await axios.post("/integrations/hubspot/authorize", {
                user_id: userId,
                org_id: orgId,
            });
            setAuthUrl(response.data.auth_url);
        };

        fetchAuthUrl();
    }, [userId, orgId]);

    const handleAuthClick = () => {
        window.open(authUrl, "_blank", "width=500,height=600");
    };

    return (
        <div>
            <h2>HubSpot Integration</h2>
            <button onClick={handleAuthClick}>Authorize HubSpot</button>
        </div>
    );
};

export default HubSpotIntegration;
