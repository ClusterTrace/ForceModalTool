# ForceModalTool
An addon for blender that adds a modal tool that creates a forcefield where the user clicks and drags

The tool works by using a raycast to find the selected object and where the ray collides on the object. Depending on whether using the closest vertex is set, the hit point or the closest vertex of the object is used as the location to place the forcefield.

Force fields are one of the only ways to adjust a clothing sim during simulation in blender (I tried other methods with very limited success).

Install by installing the ForceModalTool.py as the addon file in Blender
1. Edit -> preferences -> Add-ons
2. Then press the down arrow in the top right and select install from disk
3. Select the downloaded file (ForceModalTool.py) and select "Install From Disk"
